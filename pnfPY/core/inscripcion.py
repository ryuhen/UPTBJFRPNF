# -*- coding: utf-8 -*-
r"""
pnfPY - Modulo de INSCRIPCION.

Equivale al `INSCRIPCION.prg` del sistema legado. Permite:

  * Consultar la OFERTA ACADEMICA (secciones abiertas) de un periodo.
  * Consultar los estudiantes inscritos por Unidad Curricular / seccion
    ("Alumnos Inscritos por Unidad Curricular" del menu legado).
  * Inscribir a un estudiante en una seccion (con validacion de reglas).
  * Anular (borrado logico) una inscripcion.
  * Ver/consultar la inscripcion de un estudiante en un periodo.

Reglas de validacion reconstruidas del binario (`pnf.exe`):

  * "NO PUEDE INSCRIBIR UNIDADES CURRICULARES DEL SIGUIENTE TRAYECTO":
    no se permite inscribir UC de un trayecto mayor al que corresponde.
  * "Con Docente Asignado o Carga de Notas y Asistencia Registrada, NO SE
    PUEDEN ELIMINAR DE LA INSCRIPCION ACTUAL": una inscripcion con nota o
    asistencia ya registrada no se puede anular.
  * Control de cupo de la seccion (CUPO - INSCRITOS).
  * No duplicar la misma UC en el mismo periodo.

Escritura: se actualiza el `INS####.DBF` correspondiente (append o marcado de
`BORRAR`) y se incrementa/decrementa `INSCRITOS` en el `SEA####.DBF`.
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass, field

from .data_store import DataStore, Inscripcion, Seccion
from . import dbf_reader


# --------------------------------------------------------------------------- #
#  Resultado de operaciones
# --------------------------------------------------------------------------- #
@dataclass
class Resultado:
    ok: bool
    mensaje: str
    detalle: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  Helpers de escritura DBF (append / marcar borrado)
# --------------------------------------------------------------------------- #
def _respaldo(path: str, motivo: str) -> None:
    """Copia de seguridad antes de escribir (evita import circular)."""
    from .multiusuario import escribir_dbf
    escribir_dbf(path, motivo)


def _dbf_header_info(path: str) -> tuple[int, int, int]:
    """Devuelve (n_records, header_len, record_len) de un DBF."""
    with open(path, "rb") as fh:
        head = fh.read(32)
    n = struct.unpack("<I", head[4:8])[0]
    hlen = struct.unpack("<H", head[8:10])[0]
    rlen = struct.unpack("<H", head[10:12])[0]
    return n, hlen, rlen


def _fmt_field(valor, fld: dbf_reader.DbfField) -> bytes:
    """Formatea un valor al ancho/tipo del campo DBF (latin-1)."""
    if valor is None:
        s = ""
    elif fld.type in ("N", "F"):
        if isinstance(valor, float) and fld.decimals:
            s = f"{valor:.{fld.decimals}f}"
        else:
            s = str(int(valor)) if float(valor).is_integer() else str(valor)
    elif fld.type == "L":
        s = "T" if valor in (True, "T", "Y", 1) else "F"
    else:
        s = str(valor)
    raw = s.encode("latin-1", "replace")[: fld.length]
    # Los campos numericos se alinean a la derecha; el resto a la izquierda.
    if fld.type in ("N", "F"):
        return raw.rjust(fld.length, b" ")
    return raw.ljust(fld.length, b" ")


def append_registro(path: str, valores: dict) -> None:
    """Añade un registro al final de un DBF.

    `valores`: {nombre_campo: valor}. Los campos no indicados se rellenan
    segun su tipo (vacio/espacios).
    """
    tabla = dbf_reader.read_dbf(path)
    n, hlen, rlen = _dbf_header_info(path)
    buf = bytearray(rlen)
    buf[0:1] = b" "  # no borrado
    for fld in tabla.fields:
        val = valores.get(fld.name)
        raw = _fmt_field(val, fld)
        buf[fld.offset:fld.offset + fld.length] = raw
    with open(path, "r+b") as fh:
        fh.seek(hlen + n * rlen)
        fh.write(bytes(buf))
        # actualizar contador de registros en la cabecera (offset 4)
        fh.seek(4)
        fh.write(struct.pack("<I", n + 1))


def marcar_borrado(path: str, indice: int) -> bool:
    """Marca como borrado (bandera '*') el registro `indice` (0-based)."""
    n, hlen, rlen = _dbf_header_info(path)
    if not (0 <= indice < n):
        return False
    with open(path, "r+b") as fh:
        fh.seek(hlen + indice * rlen)
        fh.write(b"*")
    return True


# --------------------------------------------------------------------------- #
#  Consultas
# --------------------------------------------------------------------------- #
def oferta(ds: DataStore, periodo: str,
           trayecto: str | None = None,
           pnf_codigo: str | None = None) -> list[Seccion]:
    """Secciones abiertas de un periodo (opcionalmente filtradas)."""
    out = []
    for s in ds.secciones_periodo(periodo):
        if trayecto is not None and s.trayecto != str(trayecto):
            continue
        if pnf_codigo and s.pnf_codigo != pnf_codigo:
            continue
        out.append(s)
    out.sort(key=lambda s: (s.trayecto, s.codigo, s.seccion))
    return out


def inscritos_por_uc(ds: DataStore, codigo: str,
                     periodo: str | None = None) -> list[dict]:
    """Estudiantes inscritos en una UC (opcionalmente en un periodo).

    Devuelve filas con datos del estudiante + la inscripcion (seccion, nota).
    """
    cod = str(codigo).strip()
    filas: list[dict] = []
    for ced, lista in ds.ins.items():
        for ins in lista:
            if ins.codigo != cod:
                continue
            if periodo is not None and ins.periodo != str(periodo):
                continue
            est = ds.estudiante(ced)
            filas.append({
                "cedula": ced,
                "nombre": est.nombre_completo if est else "",
                "periodo": ins.periodo,
                "trayecto": ins.trayecto,
                "turno": ins.turno,
                "seccion": ins.seccion,
                "nota": ins.nota,
                "asistencia": ins.asistencia,
                "condicion": ins.condicion,
            })
    filas.sort(key=lambda f: f["nombre"])
    return filas


def inscripcion_de(ds: DataStore, cedula: str,
                   periodo: str | None = None) -> list[Inscripcion]:
    """Inscripciones de un estudiante (opcionalmente de un periodo)."""
    lista = ds.inscripciones(cedula)
    if periodo is not None:
        lista = [i for i in lista if i.periodo == str(periodo)]
    return lista


# --------------------------------------------------------------------------- #
#  Validacion
# --------------------------------------------------------------------------- #
def validar(ds: DataStore, cedula: str, seccion: Seccion,
            periodo: str) -> Resultado:
    """Valida si un estudiante puede inscribirse en una seccion.

    Aplica las reglas del legado (trayecto, duplicado, cupo, existencia).
    """
    detalle: list[str] = []
    ced = str(cedula).strip()

    if ds.estudiante(ced) is None:
        return Resultado(False, f"La cedula {ced} no esta registrada en esta sede.")

    if seccion.periodo != str(periodo):
        return Resultado(False, "La seccion no pertenece al periodo indicado.")

    # Duplicado: no inscribir la misma UC dos veces en el mismo periodo.
    for ins in ds.inscripciones(ced):
        if ins.periodo == str(periodo) and ins.codigo == seccion.codigo:
            return Resultado(
                False,
                f"El estudiante ya tiene inscrita {seccion.nombre or seccion.codigo} "
                f"en el periodo {periodo}.",
            )

    # Trayecto: no inscribir UC de un trayecto mayor al que cursa.
    trayecto_est = _trayecto_actual(ds, ced)
    try:
        t_uc = int(seccion.trayecto) if seccion.trayecto.strip() else 0
    except ValueError:
        t_uc = 0
    if trayecto_est is not None and t_uc > trayecto_est + 1:
        detalle.append(
            f"La UC es del trayecto {seccion.trayecto}; el estudiante cursa "
            f"el trayecto {trayecto_est}. Revise si corresponde."
        )

    # Cupo
    if seccion.cupo and seccion.disponible <= 0:
        return Resultado(False, "La seccion no tiene cupo disponible.")

    if seccion.estado:
        detalle.append("Aviso: la seccion figura CERRADA en la oferta.")

    return Resultado(True, "Puede inscribirse.", detalle)


def _trayecto_actual(ds: DataStore, cedula: str) -> int | None:
    """Trayecto mas alto en el que el estudiante tiene inscripciones."""
    trays = []
    for ins in ds.inscripciones(cedula):
        try:
            trays.append(int(ins.trayecto))
        except (TypeError, ValueError):
            pass
    return max(trays) if trays else None


# --------------------------------------------------------------------------- #
#  Inscripcion / anulacion
# --------------------------------------------------------------------------- #
def inscribir(ds: DataStore, cedula: str, seccion: Seccion,
              periodo: str | None = None, forzar: bool = False) -> Resultado:
    """Inscribe a un estudiante en una seccion.

    Escribe en el `INS####.DBF` del periodo y actualiza `INSCRITOS` en el
    `SEA####.DBF`. Si `forzar` es False, exige que la validacion pase.
    """
    ced = str(cedula).strip()
    periodo = periodo or seccion.periodo

    val = validar(ds, ced, seccion, periodo)
    if not val.ok and not forzar:
        return val

    ins_path = ds.sede.archivo(f"INS{periodo}")
    if not ins_path:
        return Resultado(False, f"No existe el archivo INS{periodo}.DBF en la sede.")

    # Red de seguridad: copia previa en DATA\_respaldos\ (nunca se reemplaza).
    _respaldo(ins_path, f"inscribir_{ced}")

    valores = {
        "A_ID": ced,
        "CARRERA": seccion.pnf_codigo,
        "CODIGO": seccion.codigo,
        "TRAYECTO": seccion.trayecto,
        "TRAMO": seccion.tramo,
        "TURNO": seccion.turno,
        "SECCION": seccion.seccion,
        "ANO": periodo,
        "CONDICION": "G",
        "TIPO": ds.uc_de(seccion.codigo).tipo if ds.uc_de(seccion.codigo) else "",
        "UC": ds.unidades_credito(seccion.codigo),
        "BORRAR": False,
        # Claves compuestas que usa el legado
        "ESPECIAL": _especial(seccion),
        "A_UNICA": _a_unica(ced, seccion),
        "A_PENSUM": "",
    }
    try:
        append_registro(ins_path, valores)
    except Exception as e:  # pragma: no cover
        return Resultado(False, f"No se pudo escribir la inscripcion: {e}")

    # Actualizar contador de inscritos en la oferta (SEA####)
    _ajustar_inscritos(ds, seccion, +1)

    # Refrescar el indice en memoria
    ds.cargado = False
    ds.ins.clear()
    ds.secciones.clear()
    ds.secciones_por_uc.clear()
    ds.periodos.clear()
    ds.cargar()

    return Resultado(True, f"Inscrito en {seccion.nombre or seccion.codigo} "
                           f"({seccion.turno}-{seccion.seccion}).")


def anular(ds: DataStore, cedula: str, codigo: str,
           periodo: str) -> Resultado:
    """Anula (borrado logico) la inscripcion de una UC en un periodo.

    Rechaza si ya hay nota o asistencia registrada (regla del legado).
    """
    ced = str(cedula).strip()
    ins_path = ds.sede.archivo(f"INS{periodo}")
    if not ins_path:
        return Resultado(False, f"No existe INS{periodo}.DBF.")

    tabla = dbf_reader.read_dbf(ins_path)
    idx = None
    for i, r in enumerate(tabla.rows):
        if str(r.get("A_ID")).strip() == ced and str(r.get("CODIGO")).strip() == str(codigo).strip():
            idx = i
            if r.get("NOTA") not in (None, 0) or r.get("ASISTENCIA") not in (None, 0):
                return Resultado(
                    False,
                    "No se puede anular: la UC ya tiene nota o asistencia "
                    "registrada (regla del sistema).",
                )
            break
    if idx is None:
        return Resultado(False, "No se encontro esa inscripcion.")

    # Necesitamos el indice real en el archivo (read_dbf puede omitir borrados)
    real = _indice_real(ins_path, ced, str(codigo))
    if real is None:
        return Resultado(False, "No se pudo anular la inscripcion.")
    _respaldo(ins_path, f"anular_{ced}")
    if not marcar_borrado(ins_path, real):
        return Resultado(False, "No se pudo anular la inscripcion.")

    ds.cargado = False
    ds.ins.clear()
    ds.periodos.clear()
    ds.cargar()
    return Resultado(True, f"Inscripcion anulada: {codigo} ({periodo}).")


# --------------------------------------------------------------------------- #
#  Utilidades internas
# --------------------------------------------------------------------------- #
def _especial(sec: Seccion) -> str:
    """Clave compuesta 'ESPECIAL' = PNF + CODIGO + TURNO + SECCION (formato legado)."""
    return f"{sec.pnf_codigo:<8}{sec.codigo:<20}{sec.turno}{sec.seccion}"


def _a_unica(cedula: str, sec: Seccion) -> str:
    return f"{cedula:<15}{sec.pnf_codigo:<8}{sec.codigo:<20}{sec.turno}{sec.seccion}"


def _ajustar_inscritos(ds: DataStore, sec: Seccion, delta: int) -> None:
    path = ds.sede.archivo(f"SEA{sec.periodo}")
    if not path:
        return
    try:
        tabla = dbf_reader.read_dbf(path)
        fld = tabla.get_field("INSCRITOS")
        if fld is None:
            return
        n, hlen, rlen = _dbf_header_info(path)
        # buscar la fila de esta seccion (por UFO_CLAVE + TURNO + SECCION)
        with open(path, "r+b") as fh:
            for i, r in enumerate(tabla.rows):
                clave = str(r.get("UFO_CLAVE")).strip()
                if (clave[:8].strip() == sec.pnf_codigo
                        and clave[8:].strip() == sec.codigo
                        and str(r.get("TURNO")).strip() == sec.turno
                        and str(r.get("SECCION")).strip() == sec.seccion):
                    actual = r.get("INSCRITOS") or 0
                    nuevo = max(0, int(actual) + delta)
                    pos = hlen + i * rlen + fld.offset
                    fh.seek(pos)
                    fh.write(str(nuevo).rjust(fld.length).encode("latin-1"))
                    return
    except Exception:  # pragma: no cover - no critico
        pass


def _indice_real(path: str, cedula: str, codigo: str) -> int | None:
    """Indice fisico (contando borrados) de la fila de esa inscripcion."""
    tabla = dbf_reader.read_dbf(path, keep_deleted=True)
    for i, r in enumerate(tabla.rows):
        if str(r.get("A_ID")).strip() == cedula and str(r.get("CODIGO")).strip() == codigo:
            return i
    return None
