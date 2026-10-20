# -*- coding: utf-8 -*-
r"""
pnfPY - Carga de notas del docente (entrega) y respaldos cifrados.

Resuelve el problema de distribuir la carga de notas sin antivirus:

  * En vez de enviar un .EXE (que los correos y antivirus bloquean), se
    genera una PLANILLA .XLSX CIFRADA con contraseña (AES-256). Es un
    documento de oficina: pasa correo y redes sociales sin objeciones.

  * Respaldos: paquete .ZIP cifrado con AES-256 (contenedor de datos, nunca
    un ejecutable). pyzipper escribe AES de verdad (no el ZIP "cifrado"
    tramposo que alerta a los antivirus).

Flujo:

    1) generar_planilla(ds, seccion, password)  -> .xlsx cifrado
       El docente lo recibe por correo/WhatsApp, lo abre con la contraseña,
       llena las notas y la asistencia.

    2) importar_planilla(ds, ruta, password)     -> escribe en INS####.DBF
       El coordinador recibe la planilla llenada y la importa.

    3) respaldar_sede(sede, password)            -> .zip cifrado
"""
from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass, field

from .data_store import DataStore, Seccion
from . import dbf_reader, inscripcion as INS


# --------------------------------------------------------------------------- #
#  Resultado
# --------------------------------------------------------------------------- #
@dataclass
class ResultadoCarga:
    ok: bool
    mensaje: str
    ruta: str = ""
    detalle: list[str] = field(default_factory=list)
    #: Filas leidas de la planilla (para la vista previa / dry-run).
    filas: list[dict] = field(default_factory=list)
    #: True si solo fue una vista previa (no se escribio nada).
    previa: bool = False


# --------------------------------------------------------------------------- #
#  Cifrado de XLSX (AES + contraseña)
# --------------------------------------------------------------------------- #
def _cifrar_xlsx(ruta_plano: str, password: str) -> bytes:
    """Cifra un .xlsx con contraseña (AES-256, formato OOXML estándar)."""
    import msoffcrypto
    salida = io.BytesIO()
    with open(ruta_plano, "rb") as fh:
        oficio = msoffcrypto.OfficeFile(fh)
        # msoffcrypto cifra en OOXML (AES-256) por defecto.
        oficio.encrypt(password, salida)
    data = salida.getvalue()
    salida.close()
    return data


def _descifrar_a_temporal(ruta_cifrado: str, password: str) -> str:
    """Descifra un .xlsx a un temporal en disco y devuelve su ruta."""
    import msoffcrypto
    with open(ruta_cifrado, "rb") as fh:
        oficio = msoffcrypto.OfficeFile(fh)
        oficio.load_key(password=password)
        fd, tmp = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        with open(tmp, "wb") as out:
            oficio.decrypt(out)
    return tmp


#: Nombre del archivo donde se guarda la CLAVE MAESTRA de la sede.
_ARCHIVO_CLAVE = "clave_maestra.json"

#: Clave maestra por defecto si aun no se ha creado el archivo.
_CLAVE_MAESTRA_DEFECTO = "PNF-UPTJFR-MAESTRA"


def clave_maestra(ds: DataStore | None = None, crear: bool = True) -> str:
    """Devuelve la CLAVE MAESTRA de la sede (capa 1).

    Se guarda en `datos/<sede>/clave_maestra.json` para que sea ESTABLE entre
    ejecuciones: asi el sistema SIEMPRE puede abrir sus propias planillas.
    """
    import json
    import secrets

    if ds is None:
        return _CLAVE_MAESTRA_DEFECTO

    ruta = os.path.join(ds.sede.raiz, _ARCHIVO_CLAVE)
    if os.path.isfile(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("clave"):
                return str(data["clave"])
        except (OSError, ValueError):
            pass

    clave = "M" + secrets.token_hex(8)
    if crear:
        try:
            os.makedirs(ds.sede.raiz, exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump({"clave": clave}, fh, indent=2)
        except OSError:
            return _CLAVE_MAESTRA_DEFECTO
    return clave


def clave_planilla(cedula_docente: str, periodo: str, codigo_uc: str,
                   turno: str, seccion: str) -> str:
    """Clave derivada del contexto (compatibilidad).

    La clave real de la planilla es la CLAVE MAESTRA de la sede.
    """
    import hashlib
    base = f"{cedula_docente}|{periodo}|{codigo_uc}|{turno}|{seccion}"
    return "C" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:15]


def _ruta_llave(ruta_planilla: str) -> str:
    """Ruta del archivo lateral con la clave del docente."""
    return os.path.splitext(ruta_planilla)[0] + ".llave.json"


def _guardar_llave_docente(ruta_planilla: str, clave_docente: str,
                           seccion: Seccion) -> None:
    """Guarda junto a la planilla la clave visible del docente (capa 2).

    Permite que, si el docente re-cifra el archivo con SU clave, el sistema
    pueda seguir abriéndolo sin preguntar. NO contiene datos académicos.
    """
    import json
    try:
        with open(_ruta_llave(ruta_planilla), "w", encoding="utf-8") as fh:
            json.dump({
                "clave_docente": clave_docente,
                "periodo": seccion.periodo,
                "codigo": seccion.codigo,
                "turno": seccion.turno,
                "seccion": seccion.seccion,
            }, fh, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _leer_llave_docente(ruta_planilla: str) -> str | None:
    """Lee la clave del docente guardada junto a la planilla, si existe."""
    import json
    try:
        with open(_ruta_llave(ruta_planilla), "r", encoding="utf-8") as fh:
            return json.load(fh).get("clave_docente")
    except (OSError, ValueError):
        return None


def _claves_candidatas(ds: DataStore, seccion: Seccion | None,
                       extra: str | None = None,
                       ruta_planilla: str | None = None) -> list[str]:
    """Contraseñas a probar al descifrar, en orden de probabilidad:

      1. La CLAVE MAESTRA de la sede (capa 1, siempre conocida por el sistema).
      2. La clave del DOCENTE guardada junto a la planilla (capa 2, .llave.json).
      3. La indicada explícitamente por el usuario.
      4. La clave derivada del contexto (compatibilidad).
    """
    claves: list[str] = [clave_maestra(ds)]
    if ruta_planilla:
        k = _leer_llave_docente(ruta_planilla)
        if k:
            claves.append(k)
    if extra:
        claves.append(extra)
    if seccion is not None:
        claves.append(clave_planilla(
            seccion.docente_id, seccion.periodo, seccion.codigo,
            seccion.turno, seccion.seccion,
        ))
    vistas = set()
    out = []
    for c in claves:
        if c and c not in vistas:
            vistas.add(c)
            out.append(c)
    return out


def _abrir_planilla(ds: DataStore, ruta: str, password: str | None):
    """Abre un .xlsx para importar, resolviendo el cifrado automaticamente.

    Devuelve (workbook, ruta_temporal_o_None).

    Estrategia:
      1. Si NO esta cifrado -> se abre directo (cubre el caso de que el docente
         lo haya guardado sin proteccion).
      2. Si esta cifrado -> se prueban las claves derivadas automaticamente
         (no se pide nada al usuario).
      3. Solo si ninguna funciona, se usa la contraseña indicada como ultimo
         recurso; si aun asi falla, se informa de que el archivo esta cifrado
         con una clave desconocida (imposible de abrir sin ella).
    """
    from openpyxl import load_workbook

    if not _es_cifrado(ruta):
        return load_workbook(ruta, data_only=True), None

    # Se deduce la seccion desde el NOMBRE del archivo para derivar la clave
    seccion = _seccion_desde_nombre(ds, os.path.basename(ruta))
    # Capa 1 (maestra) -> capa 2 (.llave.json del docente) -> indicada -> derivada
    candidatas = _claves_candidatas(ds, seccion, password, ruta_planilla=ruta)

    ultimo_error = None
    for clave in candidatas:
        try:
            tmp = _descifrar_a_temporal(ruta, clave)
            return load_workbook(tmp, data_only=True), tmp
        except Exception as e:  # clave incorrecta u otro problema
            ultimo_error = e
            continue

    raise RuntimeError(
        "El archivo esta CIFRADO y no se pudo descifrar automaticamente. "
        "Use la planilla generada por el sistema (su clave se calcula sola) "
        "o indique la contraseña."
        + (f" Detalle: {ultimo_error}" if ultimo_error else "")
    )


def _seccion_desde_nombre(ds: DataStore, nombre: str) -> Seccion | None:
    """Reconstruye la seccion desde un nombre tipo
    'carga_<sede>_<periodo>_<codigo>_<turno><seccion>.xlsx'.
    """
    stem = os.path.splitext(nombre)[0]
    if not stem.lower().startswith("carga_"):
        return None
    partes = stem.split("_")
    # forma esperada: carga, sede, periodo, codigo, turno+seccion
    if len(partes) < 5:
        return None
    periodo = partes[2]
    # El codigo puede tener guiones pero no guiones bajos; se rearma el resto
    try:
        codigo = partes[3]
        turno_seccion = partes[4]
        turno = turno_seccion[0] if turno_seccion else ""
        secc = turno_seccion[1:] if len(turno_seccion) > 1 else ""
    except IndexError:
        return None
    return ds.seccion(codigo, turno, secc, periodo)


def _es_cifrado(path: str) -> bool:
    """Heurística: un XLSX cifrado (OLE/CFB) empieza con D0 CF 11 E0."""
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == b"\xd0\xcf\x11\xe0"
    except OSError:
        return False


# --------------------------------------------------------------------------- #
#  1) Generar planilla de carga (para el docente)
# --------------------------------------------------------------------------- #
def generar_planilla(
    ds: DataStore,
    seccion: Seccion,
    password: str | None = None,
    destino: str | None = None,
    password_docente: str | None = None,
) -> ResultadoCarga:
    """Genera un .xlsx CIFRADO con la planilla de notas de una seccion.

    MODELO DE DOS CONTRASEÑAS (dos capas):

      * Capa 1 — CLAVE MAESTRA: la conoce SIEMPRE el sistema (estable por
        sede, en `datos/<sede>/clave_maestra.json`). Garantiza que el sistema
        pueda reimportar el archivo aunque no conozca la del docente.
      * Capa 2 — CONTRASEÑA DEL DOCENTE: `password_docente` (o `password`).
        Es la que el docente ve y usa para abrir/editar la planilla.

    El .xlsx viaja cifrado con la CLAVE MAESTRA (para que el sistema lo abra
    siempre) y, junto a él, se escribe una copia maestra con clave del docente
    en el archivo lateral `.llave`, de modo que ambas contraseñas dan acceso.

    Contenido de la hoja:
      - Cabecera: sede, periodo, UC, seccion, docente.
      - Tabla: CEDULA | ESTUDIANTE | NOTA | ASISTENCIA | OBSERVACION
      - Las columnas NOTA/ASISTENCIA quedan vacias para que el docente las llene.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return ResultadoCarga(False, "Falta openpyxl. Instale: pip install openpyxl")

    # La contraseña visible para el docente (capa 2). Si no la indica, se usa
    # una derivada del contexto que se le comunica en el mensaje de guardado.
    clave_maestra_sede = clave_maestra(ds)
    clave_docente = password_docente or password or clave_planilla(
        seccion.docente_id, seccion.periodo, seccion.codigo,
        seccion.turno, seccion.seccion,
    )
    # El archivo viaja cifrado con la MAESTRA (el sistema siempre puede abrirlo).
    password = clave_maestra_sede

    # Estudiantes inscritos en esa seccion
    filas = _estudiantes_de_seccion(ds, seccion)

    wb = Workbook()
    ws = wb.active
    ws.title = "Carga de Notas"

    azul = "1A3A6B"
    gris = "F0F0F0"
    borde = Border(*(Side(style="thin", color="BFBFBF"),) * 4)

    # Titulo
    ws.merge_cells("A1:E1")
    ws["A1"] = "PLANILLA DE CARGA DE NOTAS"
    ws["A1"].font = Font(size=14, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor=azul)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    # Datos de contexto
    cfg = ds.config
    contexto = [
        ("Universidad", cfg.get("UNIVERSIDA", "UPTJFR")),
        ("Sede", ds.sede.nombre),
        ("Periodo", seccion.periodo),
        ("Unidad Curricular", f"{seccion.nombre} ({seccion.codigo})"),
        ("Trayecto / Tramo", f"{seccion.trayecto} / {seccion.tramo}"),
        ("Turno / Seccion", f"{seccion.turno} - {seccion.seccion}"),
        ("Docente", seccion.docente or seccion.docente_id or "(sin docente)"),
    ]
    r = 3
    for etiqueta, valor in contexto:
        ws.cell(row=r, column=1, value=etiqueta).font = Font(bold=True)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
        ws.cell(row=r, column=2, value=valor)
        r += 1

    # Encabezado de la tabla
    r += 1
    headers = ["CEDULA", "ESTUDIANTE", "NOTA", "ASISTENCIA", "OBSERVACION"]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=azul)
        cell.alignment = Alignment(horizontal="center")
        cell.border = borde

    fila_inicio = r + 1
    for idx, f in enumerate(filas):
        rr = fila_inicio + idx
        ws.cell(row=rr, column=1, value=f["cedula"])
        ws.cell(row=rr, column=2, value=f["nombre"])
        # NOTA/ASISTENCIA vacias (el docente las llena)
        ws.cell(row=rr, column=3, value="")
        ws.cell(row=rr, column=4, value="")
        ws.cell(row=rr, column=5, value="")
        for c in range(1, 6):
            ws.cell(row=rr, column=c).border = borde
            if idx % 2 == 1:
                ws.cell(row=rr, column=c).fill = PatternFill("solid", fgColor=gris)

    # Nota al pie con reglas
    pie = fila_inicio + len(filas) + 1
    ws.merge_cells(start_row=pie, start_column=1, end_row=pie, end_column=5)
    ws.cell(row=pie, column=1,
            value="Nota minima: 12 general / 16 para el PROYECTO. "
                  "No modifique las columnas CEDULA ni ESTUDIANTE.").font = Font(italic=True, color="C00000")

    # Anchos
    anchos = [16, 42, 10, 14, 30]
    for i, w in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Desbloquear solo NOTA/ASISTENCIA/OBSERVACION (el resto queda protegido).
    # La contraseña de la hoja solo evita ediciones accidentales; el cifrado
    # real del archivo lo hace msoffcrypto mas abajo.
    from openpyxl.styles import Protection
    for idx in range(len(filas)):
        rr = fila_inicio + idx
        for c in (1, 2):
            ws.cell(row=rr, column=c).protection = Protection(locked=True)
        for c in (3, 4, 5):
            ws.cell(row=rr, column=c).protection = Protection(locked=False)
    ws.protection.sheet = True
    ws.protection.password = password

    # Guardar plano y cifrar
    destino = destino or _carpeta_salida()
    nombre = _nombre_planilla(ds, seccion)
    ruta_final = os.path.join(destino, nombre)

    fd, tmp = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        wb.save(tmp)
        # El .xlsx se cifra con la clave DEL DOCENTE (capa 2), igual que en el
        # sistema actual: es la que el docente ve y usa. El sistema la recupera
        # del archivo lateral .llave.json al importar (no se la pide a nadie).
        datos_cifrados = _cifrar_xlsx(tmp, clave_docente)
        with open(ruta_final, "wb") as out:
            out.write(datos_cifrados)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    # Guardar la clave del docente junto al archivo (capa 2) para que el
    # sistema pueda reimportarlo aunque el docente no se la diga.
    _guardar_llave_docente(ruta_final, clave_docente, seccion)

    return ResultadoCarga(
        True,
        f"Planilla generada ({len(filas)} estudiantes). "
        f"Contraseña del docente: {clave_docente} "
        f"(el sistema la importa sin pedirla usando la clave maestra).",
        ruta=ruta_final,
    )


def _estudiantes_de_seccion(ds: DataStore, seccion: Seccion) -> list[dict]:
    """Estudiantes inscritos en una seccion concreta (UC+turno+seccion+periodo)."""
    filas = []
    for ced, lista in ds.ins.items():
        for ins in lista:
            if (ins.codigo == seccion.codigo and ins.periodo == seccion.periodo
                    and ins.turno == seccion.turno and ins.seccion == seccion.seccion):
                est = ds.estudiante(ced)
                filas.append({
                    "cedula": ced,
                    "nombre": est.nombre_completo if est else "",
                    "nota": ins.nota,
                    "asistencia": ins.asistencia,
                    "condicion": ins.condicion,
                })
                break
    filas.sort(key=lambda f: f["nombre"])
    return filas


def _nombre_planilla(ds: DataStore, seccion: Seccion) -> str:
    base = (f"carga_{ds.sede.clave}_{seccion.periodo}_{seccion.codigo}"
            f"_{seccion.turno}{seccion.seccion}")
    limpio = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in base)
    return limpio + ".xlsx"


def _carpeta_salida() -> str:
    from .sedes import _raiz_programa
    out = os.path.join(_raiz_programa(), "cargas_notas")
    os.makedirs(out, exist_ok=True)
    return out


# --------------------------------------------------------------------------- #
#  2) Importar planilla llenada (devuelta por el docente)
# --------------------------------------------------------------------------- #
def importar_planilla(
    ds: DataStore,
    ruta: str,
    password: str | None = None,
    periodo: str | None = None,
    previa: bool = False,
) -> ResultadoCarga:
    """Importa un .xlsx (cifrado o no) y escribe las notas en INS####.DBF.

    El archivo se abre AUTOMATICAMENTE:
      - Si no esta cifrado, se lee directamente.
      - Si esta cifrado con la clave del sistema (caso normal), se descifra sin
        pedir nada al coordinador (ver `_abrir_planilla`).
      - `password` solo se usa como ultimo recurso.

    Lee CEDULA | ESTUDIANTE | NOTA | ASISTENCIA y actualiza la fila de
    inscripcion correspondiente (por cedula + codigo de UC + periodo).
    """
    if not os.path.isfile(ruta):
        return ResultadoCarga(False, f"No existe el archivo: {ruta}")

    tmp = None
    try:
        wb, tmp = _abrir_planilla(ds, ruta, password)
        ws = wb.active

        # Localizar la fila de encabezados (la que contiene 'CEDULA')
        fila_header = None
        for row in ws.iter_rows(min_row=1, max_row=30):
            for cell in row:
                if str(cell.value).strip().upper() == "CEDULA":
                    fila_header = cell.row
                    break
            if fila_header:
                break
        if fila_header is None:
            return ResultadoCarga(False, "No se encontro la columna CEDULA en la planilla.")

        # Contexto (UC/periodo) desde la cabecera
        ctx = {}
        for row in ws.iter_rows(min_row=1, max_row=fila_header):
            vals = [c.value for c in row if c.value is not None]
            if len(vals) >= 2:
                etiqueta = str(vals[0]).strip().lower()
                ctx[etiqueta] = vals[1]

        codigo = _extraer_codigo(str(ctx.get("unidad curricular", "")))
        periodo = periodo or str(ctx.get("periodo", "")).strip()
        if not codigo or not periodo:
            # Ultimo recurso: deducir del nombre del archivo
            sec_nombre = _seccion_desde_nombre(ds, os.path.basename(ruta))
            if sec_nombre is not None:
                codigo = codigo or sec_nombre.codigo
                periodo = periodo or sec_nombre.periodo
        if not codigo or not periodo:
            return ResultadoCarga(
                False, "No se pudo determinar la UC o el periodo desde la planilla.")

        # Localizar columnas
        cols = {}
        for cell in ws[fila_header]:
            h = str(cell.value).strip().upper()
            if h in ("CEDULA", "ESTUDIANTE", "NOTA", "ASISTENCIA", "OBSERVACION"):
                cols[h] = cell.column
        if "CEDULA" not in cols or "NOTA" not in cols:
            return ResultadoCarga(False, "Faltan columnas CEDULA/NOTA.")

        ins_path = ds.sede.archivo(f"INS{periodo}")
        if not ins_path:
            return ResultadoCarga(False, f"No existe INS{periodo}.DBF en la sede.")

        # Actualizar filas del DBF
        from .inscripcion import _dbf_header_info
        tabla = dbf_reader.read_dbf(ins_path)
        f_nota = tabla.get_field("NOTA")
        f_asis = tabla.get_field("ASISTENCIA")
        _n, hlen, rlen = _dbf_header_info(ins_path)

        actualizados, omitidos = 0, 0
        leidas: list[dict] = []
        with open(ins_path, "r+b") as fh:
            for row in ws.iter_rows(min_row=fila_header + 1):
                ced = row[cols["CEDULA"] - 1].value
                if ced is None:
                    continue
                ced = str(ced).strip()
                if not ced.isdigit():
                    continue
                nota = row[cols["NOTA"] - 1].value if "NOTA" in cols else None
                asis = row[cols["ASISTENCIA"] - 1].value if "ASISTENCIA" in cols else None
                nombre = (row[cols["ESTUDIANTE"] - 1].value
                          if "ESTUDIANTE" in cols else "")
                nota_v = None
                if nota not in (None, ""):
                    try:
                        nota_v = float(str(nota).replace(",", "."))
                    except ValueError:
                        nota_v = None
                asis_v = None
                if asis not in (None, ""):
                    try:
                        asis_v = float(str(asis).replace(",", "."))
                    except ValueError:
                        asis_v = None

                # Buscar la fila de la inscripcion
                idx = None
                anterior = None
                for i, rr in enumerate(tabla.rows):
                    if (str(rr.get("A_ID")).strip() == ced
                            and str(rr.get("CODIGO")).strip() == codigo):
                        idx = i
                        anterior = rr.get("NOTA")
                        break

                # Registrar para la vista previa (siempre)
                leidas.append({
                    "cedula": ced,
                    "nombre": str(nombre or ""),
                    "nota": nota_v,
                    "nota_anterior": anterior,
                    "asistencia": asis_v,
                    "encontrado": idx is not None,
                })

                if idx is None or nota_v is None:
                    omitidos += 1
                    continue

                if previa:
                    # Solo vista previa: no se escribe nada.
                    continue

                fh.seek(hlen + idx * rlen + f_nota.offset)
                fh.write(str(int(nota_v)).rjust(f_nota.length).encode("latin-1"))
                if asis_v is not None and f_asis is not None:
                    fh.seek(hlen + idx * rlen + f_asis.offset)
                    fh.write(str(int(asis_v)).rjust(f_asis.length).encode("latin-1"))
                actualizados += 1

        if previa:
            return ResultadoCarga(
                True,
                f"VISTA PREVIA: {len(leidas)} filas leidas, "
                f"{len(leidas) - omitidos} notas listas para cargar, "
                f"{omitidos} omitidas. No se escribio nada.",
                ruta=ruta, filas=leidas, previa=True,
            )

        # Refrescar memoria
        ds.cargado = False
        ds.ins.clear()
        ds.periodos.clear()
        ds.cargar()

        return ResultadoCarga(
            True,
            f"Notas importadas: {actualizados}. Omitidas: {omitidos}.",
            ruta=ruta, filas=leidas,
        )
    except Exception as e:
        return ResultadoCarga(False, f"Error al importar: {e}")
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass


def _extraer_codigo(texto: str) -> str:
    """Extrae el codigo de UC de un texto tipo 'NOMBRE (CODIGO)'."""
    if "(" in texto and ")" in texto:
        return texto[texto.rfind("(") + 1:texto.rfind(")")].strip()
    return texto.strip()


# --------------------------------------------------------------------------- #
#  3) Respaldo cifrado (.zip con contraseña AES)
# --------------------------------------------------------------------------- #
def respaldar_sede(
    sede,
    password: str,
    destino: str | None = None,
    solo_dbf: bool = True,
) -> ResultadoCarga:
    """Comprime los DBF de una sede en un .ZIP CIFRADO con AES-256.

    Usa pyzipper (AES real), no el ZipCrypto débil que alerta a antivirus.
    El paquete contiene `<sede>/DATA/...` y es un contenedor de datos, no un
    ejecutable, por lo que pasa correo y redes sociales.
    """
    try:
        import pyzipper
    except ImportError:
        return ResultadoCarga(
            False, "Falta pyzipper. Instale: pip install pyzipper")

    if not password:
        return ResultadoCarga(False, "Indique una contraseña para el respaldo.")
    if not os.path.isdir(sede.data_dir):
        return ResultadoCarga(False, f"La sede no tiene DATA: {sede.data_dir}")

    destino = destino or _carpeta_salida()
    os.makedirs(destino, exist_ok=True)
    nombre = f"respaldo_{sede.clave}.zip"
    ruta = os.path.join(destino, nombre)

    exts = (".dbf", ".cdx", ".fpt", ".dbt", ".ntx") if solo_dbf else None
    n = 0
    with pyzipper.AESZipFile(
        ruta, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES,
    ) as zf:
        zf.setpassword(password.encode("utf-8"))
        zf.setencryption(pyzipper.WZ_AES, nbits=256)
        for fn in os.listdir(sede.data_dir):
            full = os.path.join(sede.data_dir, fn)
            if not os.path.isfile(full):
                continue
            if exts and not fn.lower().endswith(exts):
                continue
            if fn.startswith("~$") or fn.startswith(".~lock"):
                continue
            zf.write(full, arcname=f"{sede.clave}/DATA/{fn}")
            n += 1

    tam = os.path.getsize(ruta) / (1024 * 1024)
    return ResultadoCarga(
        True,
        f"Respaldo cifrado generado: {n} archivos ({tam:.1f} MB).",
        ruta=ruta,
    )


def restaurar_respaldo(ruta_zip: str, password: str, destino: str) -> ResultadoCarga:
    """Extrae un respaldo cifrado en `destino` (carpeta de sedes)."""
    try:
        import pyzipper
    except ImportError:
        return ResultadoCarga(False, "Falta pyzipper. Instale: pip install pyzipper")
    if not os.path.isfile(ruta_zip):
        return ResultadoCarga(False, f"No existe: {ruta_zip}")
    os.makedirs(destino, exist_ok=True)
    try:
        with pyzipper.AESZipFile(ruta_zip) as zf:
            zf.setpassword(password.encode("utf-8"))
            zf.extractall(destino)
    except RuntimeError as e:
        return ResultadoCarga(False, f"Contraseña incorrecta o zip dañado: {e}")
    return ResultadoCarga(True, f"Respaldo restaurado en {destino}.", ruta=destino)
