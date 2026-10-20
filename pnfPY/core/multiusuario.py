# -*- coding: utf-8 -*-
r"""
pnfPY - INSCRIPCION MULTI-USUARIO (sin pisar los datos de la sede).

Problema
--------
Varias personas (coordinadores, analistas, pasantes) inscriben sobre la MISMA
carpeta ``datos\<sede>\DATA``. Si cada una enviara su copia completa de los
``INS####.DBF`` / ``SEA####.DBF``, al entregarla habria que REEMPLAZAR los
archivos de la sede y se perderia lo que inscribieron los demas.

Solucion (dos reglas simples y seguras)
---------------------------------------
1. **Escribir SIEMPRE agregando, nunca reemplazando.** Toda escritura en DBF
   pasa por :func:`escribir_dbf`, que:
     * no reescribe el archivo completo (no puede perder registros de otros),
     * solo hace *append* de filas o retoca campos puntuales (contadores),
     * guarda una copia previa en ``<DATA>\_respaldos\`` antes de tocar nada.

2. **Un "registro temporal" portatil.** Cada persona recibe una *tanda*
   (:class:`RegistroTemporal`) -> carpeta ``registros\<sede>\<tanda>\`` con los
   archivos que el programa sabe leer y fusionar::

        registros\socopo\juan_20261020_101500\
            REGISTRO.JSON          manifiesto (quien, sede, periodo, estado)
            INSCRIPCION.csv        lo que se anadio (A_ID, CODIGO, TURNO, ...)
            INSCRITOS.csv          ajustes de contador (CUPO/INSCRITOS por seccion)
            ANULADAS.csv           inscripciones anuladas (borrado logico)

   La tanda se crea **vacia** (no arrastra los datos de la sede, asi el paquete
   pesa pocos KB y no saca datos personales del equipo). Al aplicarla en la
   sede, :func:`aplicar_tanda` agrega los registros y deja constancia en
   ``<DATA>\_multiusuario\aplicados.json`` para no aplicarla dos veces.

   Como los ``INSCRIPCION.csv`` contienen cedulas, se pueden dejar en claro o
   cifrar con contrasena (AES via ``pyzipper``, o ZIP con clave del sistema si
   no esta instalado).
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import struct
import zipfile
from dataclasses import dataclass, field
from datetime import datetime

from . import dbf_reader
from .inscripcion import (
    _ajustar_inscritos, _dbf_header_info, _fmt_field,
)
from .sedes import Sede


# --------------------------------------------------------------------------- #
#  Nombres de carpetas / archivos
# --------------------------------------------------------------------------- #
REGISTROS_DIRNAME = "registros"       # <raiz del programa>\registros\<sede>\<tanda>
RESPALDOS_DIRNAME = "_respaldos"      # <DATA>\_respaldos\
MULTIUSER_DIRNAME = "_multiusuario"   # <DATA>\_multiusuario\

ARCH_MANIFIESTO = "REGISTRO.JSON"
ARCH_INS = "INSCRIPCION.csv"
ARCH_CUPOS = "INSCRITOS.csv"
ARCH_ANUL = "ANULADAS.csv"
ARCH_APLICADOS = "aplicados.json"

COL_INS = [
    "A_ID", "CARRERA", "CODIGO", "TRAYECTO", "TRAMO", "TURNO", "SECCION",
    "ANO", "CONDICION", "TIPO", "UC", "ESPECIAL", "A_UNICA",
]
COL_CUPOS = ["UFO_CLAVE", "TURNO", "SECCION", "PERIODO", "DELTA", "INSCRITOS"]
COL_ANUL = ["A_ID", "CODIGO", "ANO", "COMPROBANTE", "FECHA", "USUARIO"]


# --------------------------------------------------------------------------- #
#  Utilidades
# --------------------------------------------------------------------------- #
def _ahora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _sello() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _slug(texto: str) -> str:
    """Nombre seguro para sistema de archivos ('Juan Perez' -> 'juan_perez')."""
    limpio = re.sub(r"[^a-zA-Z0-9]+", "_", (texto or "").strip().lower())
    return limpio.strip("_") or "usuario"


def _respaldos_dir(sede: Sede) -> str:
    return os.path.join(sede.data_dir, RESPALDOS_DIRNAME)


def respaldar_archivo(path: str, motivo: str = "general") -> str | None:
    """Copia `path` a ``<DATA>\\_respaldos\\<n>_<motivo>_<sello>.dbf``.

    Devuelve la ruta del respaldo (o None si el archivo no existe). Es la red
    de seguridad: ninguna escritura toca un DBF sin dejar antes su copia.
    """
    if not os.path.isfile(path):
        return None
    destino_dir = os.path.join(os.path.dirname(path), RESPALDOS_DIRNAME)
    os.makedirs(destino_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    destino = os.path.join(destino_dir, f"{base}_{motivo}_{_sello()}.DBF")
    shutil.copy2(path, destino)
    return destino


def escribir_dbf(path: str, motivo: str = "general") -> str | None:
    """PREPARA una escritura sobre `path`: respalda y devuelve la copia.

    Uso: se llama ANTES de cualquier append/marcado. Deja rastro en
    ``_multiusuario/eventos.log`` para saber quien escribio y cuando.
    """
    respaldo = respaldar_archivo(path, motivo)
    _registrar_evento(os.path.dirname(path), f"escritura {os.path.basename(path)} "
                                             f"motivo={motivo} respaldo={respaldo}")
    return respaldo


def _registrar_evento(data_dir: str, texto: str) -> None:
    carpeta = os.path.join(data_dir, MULTIUSER_DIRNAME)
    try:
        os.makedirs(carpeta, exist_ok=True)
        with open(os.path.join(carpeta, "eventos.log"), "a", encoding="utf-8") as fh:
            fh.write(f"{_ahora()}\t{os.environ.get('USERNAME', '?')}\t{texto}\n")
    except OSError:  # pragma: no cover - no critico
        pass


def _leer_csv(path: str, columnas: list[str]) -> list[dict]:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return [{c: (r.get(c) or "") for c in columnas} for r in csv.DictReader(fh)]


def _escribir_csv(path: str, columnas: list[str], filas: list[dict]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas)
        w.writeheader()
        for f in filas:
            w.writerow({c: f.get(c, "") for c in columnas})


def _leer_json(path: str, defecto=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return defecto


def _escribir_json(path: str, datos) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
#  Registro temporal (tanda) de una persona
# --------------------------------------------------------------------------- #
@dataclass
class RegistroTemporal:
    """Carpeta de trabajo de una persona para inscribir sin tocar la sede."""

    ruta: str
    usuario: str
    sede_clave: str
    periodo: str
    estado: str = "abierto"          # abierto | cerrado | aplicado
    creado: str = field(default_factory=_ahora)
    dispositivo: str = ""
    notas: str = ""

    # --- rutas --------------------------------------------------------- #
    @property
    def archivo_ins(self) -> str:
        return os.path.join(self.ruta, ARCH_INS)

    @property
    def archivo_cupos(self) -> str:
        return os.path.join(self.ruta, ARCH_CUPOS)

    @property
    def archivo_anuladas(self) -> str:
        return os.path.join(self.ruta, ARCH_ANUL)

    @property
    def archivo_manifiesto(self) -> str:
        return os.path.join(self.ruta, ARCH_MANIFIESTO)

    # --- lectura ------------------------------------------------------- #
    def inscripciones(self) -> list[dict]:
        return _leer_csv(self.archivo_ins, COL_INS)

    def cupos(self) -> list[dict]:
        return _leer_csv(self.archivo_cupos, COL_CUPOS)

    def anuladas(self) -> list[dict]:
        return _leer_csv(self.archivo_anuladas, COL_ANUL)

    def manifiesto(self) -> dict:
        return _leer_json(self.archivo_manifiesto, {}) or {}

    # --- estado -------------------------------------------------------- #
    def guardar(self) -> None:
        _escribir_json(self.archivo_manifiesto, {
            "usuario": self.usuario,
            "sede": self.sede_clave,
            "periodo": self.periodo,
            "estado": self.estado,
            "creado": self.creado,
            "actualizado": _ahora(),
            "dispositivo": self.dispositivo,
            "notas": self.notas,
            "inscripciones": len(self.inscripciones()),
            "anuladas": len(self.anuladas()),
        })

    def cerrar(self) -> None:
        self.estado = "cerrado"
        self.guardar()

    # --- anotaciones --------------------------------------------------- #
    def anotar_inscripcion(self, fila: dict) -> None:
        filas = self.inscripciones()
        filas.append({c: fila.get(c, "") for c in COL_INS})
        _escribir_csv(self.archivo_ins, COL_INS, filas)
        self.guardar()

    def anotar_cupo(self, ufo_clave: str, turno: str, seccion: str,
                    periodo: str, delta: int) -> None:
        """Acumula el ajuste de INSCRITOS para esa seccion."""
        filas = self.cupos()
        for f in filas:
            if (f["UFO_CLAVE"] == ufo_clave and f["TURNO"] == turno
                    and f["SECCION"] == seccion and f["PERIODO"] == str(periodo)):
                f["DELTA"] = str(int(f["DELTA"] or 0) + delta)
                break
        else:
            filas.append({
                "UFO_CLAVE": ufo_clave, "TURNO": turno, "SECCION": seccion,
                "PERIODO": str(periodo), "DELTA": str(delta), "INSCRITOS": "",
            })
        _escribir_csv(self.archivo_cupos, COL_CUPOS, filas)
        self.guardar()

    def anotar_anulacion(self, cedula: str, codigo: str, periodo: str) -> None:
        filas = self.anuladas()
        filas.append({
            "A_ID": cedula, "CODIGO": codigo, "ANO": str(periodo),
            "COMPROBANTE": "", "FECHA": _ahora(),
            "USUARIO": self.usuario,
        })
        _escribir_csv(self.archivo_anuladas, COL_ANUL, filas)
        self.guardar()


# --------------------------------------------------------------------------- #
#  Crear / abrir / listar tandas
# --------------------------------------------------------------------------- #
def raiz_registros() -> str:
    from .sedes import RAIZ
    return os.path.join(RAIZ, REGISTROS_DIRNAME)


def crear_tanda(sede: Sede, usuario: str, periodo: str,
                destino: str | None = None, notas: str = "") -> RegistroTemporal:
    """Crea una tanda vacia (compacta) para que una persona inscriba.

    No copia los DBF de la sede: solamente crea los CSV de trabajo. Asi el
    paquete es pequeno y no saca datos personales del equipo de la sede.
    """
    base = destino or os.path.join(raiz_registros(), sede.clave)
    ruta = os.path.join(base, f"{_slug(usuario)}_{_sello()}")
    os.makedirs(ruta, exist_ok=True)

    tanda = RegistroTemporal(
        ruta=ruta, usuario=usuario.strip() or "usuario",
        sede_clave=sede.clave, periodo=str(periodo),
        dispositivo=os.environ.get("COMPUTERNAME", ""), notas=notas,
    )
    _escribir_csv(tanda.archivo_ins, COL_INS, [])
    _escribir_csv(tanda.archivo_cupos, COL_CUPOS, [])
    _escribir_csv(tanda.archivo_anuladas, COL_ANUL, [])
    tanda.guardar()
    _registrar_evento(sede.data_dir, f"tanda creada {usuario} -> {ruta}")
    return tanda


def abrir_tanda(ruta: str) -> RegistroTemporal | None:
    """Carga una tanda existente (carpeta) a partir de su REGISTRO.JSON."""
    man = _leer_json(os.path.join(ruta, ARCH_MANIFIESTO))
    if not isinstance(man, dict):
        return None
    return RegistroTemporal(
        ruta=ruta,
        usuario=man.get("usuario", "usuario"),
        sede_clave=man.get("sede", ""),
        periodo=str(man.get("periodo", "")),
        estado=man.get("estado", "abierto"),
        creado=man.get("creado", ""),
        dispositivo=man.get("dispositivo", ""),
        notas=man.get("notas", ""),
    )


def listar_tandas(sede: Sede | None = None,
                  base: str | None = None) -> list[RegistroTemporal]:
    """Lista las tandas (carpetas con REGISTRO.JSON) de una sede o de todas."""
    base = base or raiz_registros()
    if not os.path.isdir(base):
        return []
    raices = ([os.path.join(base, sede.clave)] if sede
              else [os.path.join(base, d) for d in sorted(os.listdir(base))])
    out: list[RegistroTemporal] = []
    for raiz in raices:
        if not os.path.isdir(raiz):
            continue
        for d in sorted(os.listdir(raiz)):
            ruta = os.path.join(raiz, d)
            if os.path.isdir(ruta):
                t = abrir_tanda(ruta)
                if t is not None:
                    out.append(t)
    return out


# --------------------------------------------------------------------------- #
#  Empaquetar / descomprimir la tanda para enviarla
# --------------------------------------------------------------------------- #
def empaquetar(tanda: RegistroTemporal, password: str | None = None) -> str:
    """Comprime la tanda en un .zip listo para enviar por correo/USB.

    Con `password` usa AES (pyzipper); si no esta instalado cae a ZIP normal.
    """
    destino = f"{tanda.ruta}.zip"
    archivos = [f for f in (ARCH_MANIFIESTO, ARCH_INS, ARCH_CUPOS, ARCH_ANUL)
                if os.path.isfile(os.path.join(tanda.ruta, f))]
    if password:
        try:
            import pyzipper  # type: ignore
            with pyzipper.AESZipFile(destino, "w",
                                     compression=pyzipper.ZIP_DEFLATED,
                                     encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode("utf-8"))
                for f in archivos:
                    zf.write(os.path.join(tanda.ruta, f), arcname=f)
            return destino
        except ImportError:
            pass
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in archivos:
            zf.write(os.path.join(tanda.ruta, f), arcname=f)
    return destino


def extraer_paquete(zip_path: str, password: str | None = None) -> RegistroTemporal:
    """Descomprime un .zip de tanda en ``registros\\_recibidos\\`` y lo abre."""
    destino = os.path.join(raiz_registros(), "_recibidos",
                           os.path.splitext(os.path.basename(zip_path))[0])
    os.makedirs(destino, exist_ok=True)
    aes = False
    if password:
        try:
            import pyzipper  # type: ignore  # noqa: F401
            aes = True
        except ImportError:
            aes = False

    if aes:
        import pyzipper  # type: ignore
        with pyzipper.AESZipFile(zip_path) as zf:
            zf.setpassword(password.encode("utf-8"))
            for info in zf.infolist():
                nombre = os.path.basename(info.filename)
                if nombre:
                    with open(os.path.join(destino, nombre), "wb") as out:
                        out.write(zf.read(info))
    else:
        with zipfile.ZipFile(zip_path) as zf:
            pwd = password.encode("utf-8") if password else None
            for info in zf.infolist():
                nombre = os.path.basename(info.filename)
                if not nombre:
                    continue
                try:
                    datos = zf.read(info, pwd=pwd)
                except RuntimeError as e:
                    raise ValueError(
                        f"No se pudo abrir {zip_path}: {e}. Si el paquete usa "
                        f"AES instale pyzipper (pip install pyzipper).") from e
                with open(os.path.join(destino, nombre), "wb") as out:
                    out.write(datos)

    tanda = abrir_tanda(destino)
    if tanda is None:
        raise ValueError(f"{zip_path} no contiene un {ARCH_MANIFIESTO} valido.")
    return tanda


# --------------------------------------------------------------------------- #
#  Aplicar la tanda a la sede: AGREGAR, nunca reemplazar
# --------------------------------------------------------------------------- #
@dataclass
class ResultadoAplicacion:
    ok: bool
    mensaje: str
    agregadas: int = 0
    omitidas: int = 0
    anuladas: int = 0
    cupos: int = 0
    detalle: list[str] = field(default_factory=list)


def huella(tanda: RegistroTemporal) -> str:
    """Huella estable de la tanda (sirve aunque se descomprima en otra ruta)."""
    import hashlib
    h = hashlib.sha1()
    h.update(f"{tanda.usuario}|{tanda.sede_clave}|{tanda.periodo}".encode("utf-8"))
    for f in (ARCH_INS, ARCH_CUPOS, ARCH_ANUL):
        ruta = os.path.join(tanda.ruta, f)
        if os.path.isfile(ruta):
            with open(ruta, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:16]


def _ya_aplicada(sede: Sede, tanda: RegistroTemporal) -> bool:
    archivo = os.path.join(sede.data_dir, MULTIUSER_DIRNAME, ARCH_APLICADOS)
    aplicados = _leer_json(archivo, []) or []
    clave = huella(tanda)
    return any(a.get("huella") == clave or a.get("ruta") == tanda.ruta
               for a in aplicados)


def _marcar_aplicada(sede: Sede, tanda: RegistroTemporal,
                     res: ResultadoAplicacion) -> None:
    archivo = os.path.join(sede.data_dir, MULTIUSER_DIRNAME, ARCH_APLICADOS)
    aplicados = _leer_json(archivo, []) or []
    aplicados.append({
        "huella": huella(tanda), "ruta": tanda.ruta,
        "usuario": tanda.usuario, "sede": tanda.sede_clave,
        "periodo": tanda.periodo, "fecha": _ahora(),
        "agregadas": res.agregadas, "anuladas": res.anuladas,
        "omitidas": res.omitidas,
    })
    _escribir_json(archivo, aplicados)


def _agregar_fila(path: str, valores: dict) -> bool:
    """Append puro: NO reescribe el archivo, solo anade al final."""
    tabla = dbf_reader.read_dbf(path)
    n, hlen, rlen = _dbf_header_info(path)
    buf = bytearray(rlen)
    buf[0:1] = b" "
    for fld in tabla.fields:
        buf[fld.offset:fld.offset + fld.length] = _fmt_field(valores.get(fld.name), fld)
    with open(path, "r+b") as fh:
        fh.seek(hlen + n * rlen)
        fh.write(bytes(buf))
        fh.seek(4)
        fh.write(struct.pack("<I", n + 1))
    return True


def _existe_inscripcion(path: str, cedula: str, codigo: str) -> int | None:
    tabla = dbf_reader.read_dbf(path, keep_deleted=True,
                               fields={"A_ID", "CODIGO"})
    for i, r in enumerate(tabla.rows):
        if (str(r.get("A_ID")).strip() == cedula.strip()
                and str(r.get("CODIGO")).strip() == codigo.strip()
                and not r.get("_DELETED")):
            return i
    return None


def _borrar_por_comprobante(path: str, cedula: str, codigo: str) -> bool:
    idx = _existe_inscripcion(path, cedula, codigo)
    if idx is None:
        return False
    _n, hlen, rlen = _dbf_header_info(path)  # _n: no se usa
    with open(path, "r+b") as fh:
        fh.seek(hlen + idx * rlen)
        fh.write(b"*")
    return True

def aplicar_tanda(sede: Sede, tanda: RegistroTemporal,
                  usuario: str | None = None) -> ResultadoAplicacion:
    """Agrega a la sede las inscripciones/anulaciones de la tanda.

    Reglas:
      * Si la tanda ya se aplico a esta sede -> no hace nada (idempotente).
      * Si la cedula+UC ya esta inscrita -> se OMITE (no se duplica).
      * Solo se hace append al INS####.DBF y se retoca INSCRITOS en SEA####.
      * Antes de escribir se respalda cada DBF en ``_respaldos\\``.
    """
    quimico = usuario or os.environ.get("USERNAME", "usuario")
    if _ya_aplicada(sede, tanda):
        return ResultadoAplicacion(
            False, f"La tanda de {tanda.usuario} ya fue aplicada a {sede.nombre}.")

    ins_path = sede.archivo(f"INS{tanda.periodo}")
    if not ins_path:
        return ResultadoAplicacion(
            False, f"No existe INS{tanda.periodo}.DBF en {sede.nombre}.")

    res = ResultadoAplicacion(True, "")
    filas = tanda.inscripciones()
    if filas:
        escribir_dbf(ins_path, f"tanda_{_slug(tanda.usuario)}")

    for f in filas:
        ced = (f.get("A_ID") or "").strip()
        cod = (f.get("CODIGO") or "").strip()
        if not ced or not cod:
            continue
        if _existe_inscripcion(ins_path, ced, cod) is not None:
            res.omitidas += 1
            res.detalle.append(f"OMITIDA (ya inscrita): {ced} {cod}")
            continue
        valores = {c: f.get(c, "") for c in COL_INS}
        _agregar_fila(ins_path, valores)
        res.agregadas += 1
        res.detalle.append(f"AGREGADA: {ced} {cod} {f.get('TURNO','')}{f.get('SECCION','')}")

    # Anulaciones (borrado logico) antes de ajustar contadores
    for f in tanda.anuladas():
        ced = (f.get("A_ID") or "").strip()
        cod = (f.get("CODIGO") or "").strip()
        if not ced or not cod:
            continue
        if _borrar_por_comprobante(ins_path, ced, cod):
            res.anuladas += 1
            res.detalle.append(f"ANULADA: {ced} {cod}")

    # Contadores INSCRITOS: se recalcula desde el INS real (no se suma a ciegas)
    for c in tanda.cupos():
        try:
            delta = int(c.get("DELTA") or 0)
        except ValueError:
            delta = 0
        if not delta:
            continue
        _ajustar_inscritos_por_clave(sede, c.get("UFO_CLAVE", ""),
                                     c.get("TURNO", ""), c.get("SECCION", ""),
                                     c.get("PERIODO") or tanda.periodo, delta)
        res.cupos += 1

    _marcar_aplicada(sede, tanda, res)
    _registrar_evento(sede.data_dir,
                      f"tanda aplicada de {tanda.usuario}: +{res.agregadas} "
                      f"omitidas={res.omitidas} anuladas={res.anuladas} por {quimico}")
    tanda.estado = "aplicado"
    tanda.guardar()
    res.mensaje = (f"Tanda de {tanda.usuario}: {res.agregadas} agregadas, "
                   f"{res.omitidas} omitidas, {res.anuladas} anuladas.")
    return res


def _ajustar_inscritos_por_clave(sede: Sede, ufo_clave: str, turno: str,
                                 seccion: str, periodo: str, delta: int) -> None:
    path = sede.archivo(f"SEA{periodo}")
    if not path:
        return
    tabla = dbf_reader.read_dbf(path)
    fld = tabla.get_field("INSCRITOS")
    if fld is None:
        return
    _n, hlen, rlen = _dbf_header_info(path)  # _n: no se usa
    escribir_dbf(path, "contador_inscritos")
    with open(path, "r+b") as fh:
        for i, r in enumerate(tabla.rows):
            if (str(r.get("UFO_CLAVE")).strip() == ufo_clave.strip()
                    and str(r.get("TURNO")).strip() == turno.strip()
                    and str(r.get("SECCION")).strip() == seccion.strip()):
                nuevo = max(0, int(r.get("INSCRITOS") or 0) + delta)
                fh.seek(hlen + i * rlen + fld.offset)
                fh.write(str(nuevo).rjust(fld.length).encode("latin-1"))
                return


# --------------------------------------------------------------------------- #
#  Estado de las tandas (para GUI/CLI)
# --------------------------------------------------------------------------- #
def resumen_multiusuario(sede: Sede) -> dict:
    """Cuenta inscripciones reales, tandas pendientes y ultima aplicacion."""
    tandas = [t for t in listar_tandas(sede) if t.estado != "aplicado"]
    archivo = os.path.join(sede.data_dir, MULTIUSER_DIRNAME, ARCH_APLICADOS)
    aplicados = _leer_json(archivo, []) or []
    return {
        "sede": sede.nombre,
        "data_dir": sede.data_dir,
        "registros_dir": os.path.join(raiz_registros(), sede.clave),
        "tandas": tandas,
        "aplicadas": aplicados,
        "ultima": aplicados[-1] if aplicados else None,
        "respaldos": _contar_respaldos(sede),
    }


def _contar_respaldos(sede: Sede) -> int:
    carpeta = _respaldos_dir(sede)
    if not os.path.isdir(carpeta):
        return 0
    return len([f for f in os.listdir(carpeta) if f.upper().endswith(".DBF")])

