# -*- coding: utf-8 -*-
"""
pnfPY - Carga e indice de los datos de UNA sede.

Equivalente multi-sede de lo que hace el sistema legado al abrirse: lee
`ALM.DBF` (estudiantes), `UFO.DBF` (unidades curriculares), `PNF.DBF`
(carreras), `CONFIG.DBF` (parametros de la sede), `DCT.DBF` (docentes) y
todos los `INS####[IP].DBF` (inscripciones/notas).

Todo se indexa por cedula para que las funcionalidades (historial, constancia,
inscripcion, notas, grado) consulten rapido.

Importante: cada `DataStore` pertenece a UNA sede. Para trabajar las cuatro
sedes a la vez se crean cuatro `DataStore` (ver `core.registro`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import dbf_reader
from .sedes import Sede


# --------------------------------------------------------------------------- #
#  Estructuras de dominio
# --------------------------------------------------------------------------- #
@dataclass
class Inscripcion:
    """Una fila de un INS####[IP].DBF (inscripcion de una UC en un periodo)."""

    anio: int
    sufijo: str                 # '' regular, 'I' intersemestral, 'P' PER
    carrera: str
    codigo: str                 # codigo de la UC
    trayecto: str
    tramo: str
    turno: str
    seccion: str
    nota: float | None
    asistencia: float | None
    condicion: str
    tipo: str
    uc: int
    borrar: bool = False

    @property
    def periodo(self) -> str:
        return f"{self.anio}{self.sufijo}"

    @property
    def orden(self) -> tuple[int, str]:
        return (self.anio, {"": "0", "I": "1", "P": "2"}.get(self.sufijo, "9"))


@dataclass
class UC:
    """Una unidad curricular del catalogo (UFO.DBF)."""

    clave: str
    pnf_codigo: str
    codigo: str
    nombre: str
    trayecto: str
    tramo: str
    uc: int
    tipo: str
    hta: int = 0
    hti: int = 0
    htt: int = 0


@dataclass
class Estudiante:
    """Una fila de ALM.DBF."""

    cedula: str
    nombre: str
    apellido: str
    ingreso: str
    telefono: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def nombre_completo(self) -> str:
        return f"{self.apellido}, {self.nombre}".strip(", ")


@dataclass
class RegistroAcademico:
    """Registro academico del estudiante (fila de CC.DBF).

    Indica su PNF, turno, si esta activo y su situacion (regular, retirado...).
    """

    cedula: str
    pnf_codigo: str
    pnf_nombre: str
    turno: str
    activo: bool
    ingreso: str
    situacion: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Seccion:
    """Una seccion abierta / oferta academica (fila de SEA####.DBF)."""

    anio: int
    sufijo: str                 # '' regular, 'I' intersemestral, 'P' PER
    pnf_codigo: str
    codigo: str                 # codigo de la UC
    ufo_clave: str
    nombre: str                 # nombre de la UC
    trayecto: str
    tramo: str
    turno: str                  # D / F / ...
    turno_c: str                # 'DIURNO' / 'FIN DE SEMANA'
    seccion: str                # letra de la seccion
    cupo: int
    inscritos: int
    docente_id: str
    docente: str
    estado: bool                # True = abierta

    @property
    def periodo(self) -> str:
        return f"{self.anio}{self.sufijo}"

    @property
    def disponible(self) -> int:
        return max(0, self.cupo - self.inscritos)

    @property
    def clave_seccion(self) -> tuple[str, str, str, str]:
        """Identidad de la seccion: (codigo UC, turno, seccion, periodo)."""
        return (self.codigo, self.turno, self.seccion, self.periodo)


# --------------------------------------------------------------------------- #
#  Helpers de conversion
# --------------------------------------------------------------------------- #
def _int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().upper() in ("T", "Y", "1", "S", "SI")


# --------------------------------------------------------------------------- #
#  DataStore
# --------------------------------------------------------------------------- #
class DataStore:
    """Datos de una sede leidos desde sus DBF."""

    def __init__(self, sede: Sede):
        self.sede = sede
        self.config: dict[str, str] = {}
        self.estudiantes: dict[str, Estudiante] = {}
        self.ufo: dict[str, UC] = {}                 # codigo UC -> UC
        self.ufo_por_clave: dict[str, UC] = {}       # UFO_CLAVE -> UC
        self.pnf: dict[str, dict] = {}               # codigo PNF -> fila
        self.docentes: dict[str, dict] = {}          # cedula -> fila
        self.cc: dict[str, RegistroAcademico] = {}   # cedula -> registro academico
        self.ins: dict[str, list[Inscripcion]] = {}  # cedula -> inscripciones
        self.secciones: dict[tuple, Seccion] = {}     # clave_seccion -> Seccion
        self.secciones_por_uc: dict[str, list[Seccion]] = {}  # codigo UC -> secciones
        self.periodos: list[tuple[int, str, str]] = []
        self.faltantes_uc: set[str] = set()
        self.cargado = False
        self.advertencias: list[str] = []

    # ------------------------------------------------------------------ #
    #  Carga
    # ------------------------------------------------------------------ #
    def cargar(self, incluir_intersemestral: bool = True) -> "DataStore":
        """Carga toda la sede. Idempotente (si ya cargo, no repite)."""
        if self.cargado:
            return self
        self._cargar_config()
        self._cargar_pnf()
        self._cargar_ufo()
        self._cargar_estudiantes()
        self._cargar_cc()
        self._cargar_docentes()
        self._cargar_inscripciones(incluir_intersemestral)
        self._cargar_secciones(incluir_intersemestral)
        self.cargado = True
        return self

    def _cargar_config(self) -> None:
        path = self.sede.archivo("CONFIG")
        if not path:
            self.advertencias.append("No se encontro CONFIG.DBF")
            return
        try:
            tabla = dbf_reader.read_dbf(path)
            if tabla.rows:
                fila = tabla.rows[0]
                self.config = {k: _str(v) for k, v in fila.items()}
        except Exception as e:  # pragma: no cover - defensivo
            self.advertencias.append(f"CONFIG.DBF: {e}")

    def _cargar_pnf(self) -> None:
        path = self.sede.archivo("PNF")
        if not path:
            return
        try:
            for r in dbf_reader.read_dbf(path).rows:
                codigo = _str(r.get("PNF_CODIGO") or r.get("CODIGO") or r.get("CLAVE"))
                if codigo:
                    self.pnf[codigo] = r
        except Exception as e:  # pragma: no cover
            self.advertencias.append(f"PNF.DBF: {e}")

    def _cargar_ufo(self) -> None:
        path = self.sede.archivo("UFO")
        if not path:
            self.advertencias.append("No se encontro UFO.DBF")
            return
        campos = {
            "UFO_CLAVE", "PNF_CODIGO", "CODIGO", "UFO_NOMBRE",
            "TRAYECTO", "TRAMO", "UC", "TIPO", "HTA", "HTI", "HTT",
        }
        try:
            for r in dbf_reader.read_dbf(path, fields=campos).rows:
                codigo = _str(r.get("CODIGO"))
                if not codigo:
                    continue
                uc = UC(
                    clave=_str(r.get("UFO_CLAVE")),
                    pnf_codigo=_str(r.get("PNF_CODIGO")),
                    codigo=codigo,
                    nombre=_str(r.get("UFO_NOMBRE")),
                    trayecto=_str(r.get("TRAYECTO")),
                    tramo=_str(r.get("TRAMO")),
                    uc=_int(r.get("UC")),
                    tipo=_str(r.get("TIPO")).upper(),
                    hta=_int(r.get("HTA")),
                    hti=_int(r.get("HTI")),
                    htt=_int(r.get("HTT")),
                )
                # El catalogo puede tener la misma UC repetida por plan; se
                # conserva la ultima (la mas reciente en el archivo).
                self.ufo[codigo] = uc
                if uc.clave:
                    self.ufo_por_clave[uc.clave] = uc
        except Exception as e:  # pragma: no cover
            self.advertencias.append(f"UFO.DBF: {e}")

    def _cargar_estudiantes(self) -> None:
        path = self.sede.archivo("ALM")
        if not path:
            self.advertencias.append("No se encontro ALM.DBF")
            return
        campos = {
            # Nombres habituales en el legado
            "A_ID", "A_NOMBRE", "A_APELLIDO", "A_FINGRESO", "A_TEL1",
            "A_PNF", "A_PENSUM", "CEDULA", "NOMBRE", "APELLIDO",
        }
        try:
            for r in dbf_reader.read_dbf(path, fields=campos).rows:
                cedula = _str(r.get("A_ID") or r.get("CEDULA"))
                if not cedula:
                    continue
                self.estudiantes[cedula] = Estudiante(
                    cedula=cedula,
                    nombre=_str(r.get("A_NOMBRE") or r.get("NOMBRE")),
                    apellido=_str(r.get("A_APELLIDO") or r.get("APELLIDO")),
                    ingreso=_str(r.get("A_FINGRESO")),
                    telefono=_str(r.get("A_TEL1")),
                    raw=r,
                )
        except Exception as e:  # pragma: no cover
            self.advertencias.append(f"ALM.DBF: {e}")

    def _cargar_cc(self) -> None:
        """Carga el registro academico del estudiante (CC.DBF)."""
        path = self.sede.archivo("CC")
        if not path:
            return
        campos = {
            "A_ID", "PNF_CODIGO", "PNF_NOMBRE", "TURNO", "ACTIVO",
            "A_INGRESO", "A_SITUACIO",
        }
        try:
            for r in dbf_reader.read_dbf(path, fields=campos).rows:
                ced = _str(r.get("A_ID"))
                if not ced:
                    continue
                self.cc[ced] = RegistroAcademico(
                    cedula=ced,
                    pnf_codigo=_str(r.get("PNF_CODIGO")),
                    pnf_nombre=_str(r.get("PNF_NOMBRE")),
                    turno=_str(r.get("TURNO")),
                    activo=_bool(r.get("ACTIVO")),
                    ingreso=_str(r.get("A_INGRESO")),
                    situacion=_str(r.get("A_SITUACIO")),
                    raw=r,
                )
        except Exception as e:  # pragma: no cover
            self.advertencias.append(f"CC.DBF: {e}")

    def _cargar_docentes(self) -> None:
        path = self.sede.archivo("DCT")
        if not path:
            return
        try:
            for r in dbf_reader.read_dbf(path).rows:
                cedula = _str(r.get("D_ID") or r.get("CEDULA") or r.get("D_CEDULA"))
                if cedula:
                    self.docentes[cedula] = r
        except Exception as e:  # pragma: no cover
            self.advertencias.append(f"DCT.DBF: {e}")

    def _cargar_inscripciones(self, incluir_intersemestral: bool) -> None:
        campos_ins = {
            "A_ID", "CARRERA", "CODIGO", "TRAYECTO", "TRAMO", "TURNO",
            "SECCION", "ANO", "NOTA", "ASISTENCIA", "CONDICION", "TIPO",
            "UC", "BORRAR", "CEDULA",
        }
        for anio, suf, path in self.sede.periodos():
            if suf == "I" and not incluir_intersemestral:
                continue
            self.periodos.append((anio, suf, path))
            try:
                tabla = dbf_reader.read_dbf(path, fields=campos_ins)
            except Exception as e:  # pragma: no cover
                self.advertencias.append(f"{path}: {e}")
                continue
            for r in tabla.rows:
                cedula = _str(r.get("A_ID") or r.get("CEDULA"))
                codigo = _str(r.get("CODIGO"))
                if not cedula or not codigo:
                    continue
                borrar = _bool(r.get("BORRAR"))
                ins = Inscripcion(
                    anio=anio,
                    sufijo=suf,
                    carrera=_str(r.get("CARRERA")),
                    codigo=codigo,
                    trayecto=_str(r.get("TRAYECTO")),
                    tramo=_str(r.get("TRAMO")),
                    turno=_str(r.get("TURNO")),
                    seccion=_str(r.get("SECCION")),
                    nota=_float(r.get("NOTA")),
                    asistencia=_float(r.get("ASISTENCIA")),
                    condicion=_str(r.get("CONDICION")),
                    tipo=_str(r.get("TIPO")).upper(),
                    uc=_int(r.get("UC")),
                    borrar=borrar,
                )
                if borrar:
                    continue
                self.ins.setdefault(cedula, []).append(ins)
                if codigo not in self.ufo:
                    self.faltantes_uc.add(codigo)

        # Orden cronologico dentro de cada estudiante
        for lst in self.ins.values():
            lst.sort(key=lambda i: i.orden)

    def _cargar_secciones(self, incluir_intersemestral: bool) -> None:
        """Carga la OFERTA ACADEMICA (secciones abiertas) de los SEA####[IP].DBF.

        Cada fila SEA es una seccion abierta de una UC en un periodo, con su
        cupo, inscritos, docente, turno y letra de seccion. Es la base para
        saber que se puede inscribir.
        """
        campos_sea = {
            "ESTADO", "CUPO", "INSCRITOS", "UFO_CLAVE", "TRAYECTO", "TURNO",
            "SECCION", "ANO", "D_ID", "UFO_NOMBRE", "PNF_CODIGO", "D_NOMBRE",
            "TRAMO", "TURNO_C",
        }
        for anio, suf, _ins_path in self.periodos:
            if suf == "I" and not incluir_intersemestral:
                continue
            path = self.sede.archivo(f"SEA{anio}{suf}")
            if not path:
                continue
            try:
                tabla = dbf_reader.read_dbf(path, fields=campos_sea)
            except Exception as e:  # pragma: no cover
                self.advertencias.append(f"SEA{anio}{suf}: {e}")
                continue
            for r in tabla.rows:
                codigo = _str(r.get("UFO_CLAVE"))
                # UFO_CLAVE = PNF_CODIGO(8) + CODIGO(20)  -> extraemos el codigo
                ufo_clave = codigo
                if not codigo:
                    continue
                cod_uc = codigo[8:].strip() if len(codigo) > 8 else codigo
                sec = Seccion(
                    anio=anio, sufijo=suf,
                    pnf_codigo=_str(r.get("PNF_CODIGO")) or codigo[:8].strip(),
                    codigo=cod_uc,
                    ufo_clave=ufo_clave,
                    nombre=_str(r.get("UFO_NOMBRE")),
                    trayecto=_str(r.get("TRAYECTO")),
                    tramo=_str(r.get("TRAMO")),
                    turno=_str(r.get("TURNO")),
                    turno_c=_str(r.get("TURNO_C")),
                    seccion=_str(r.get("SECCION")),
                    cupo=_int(r.get("CUPO")),
                    inscritos=_int(r.get("INSCRITOS")),
                    docente_id=_str(r.get("D_ID")),
                    docente=_str(r.get("D_NOMBRE")),
                    estado=_bool(r.get("ESTADO")),
                )
                self.secciones[sec.clave_seccion] = sec
                self.secciones_por_uc.setdefault(sec.codigo, []).append(sec)

    # ------------------------------------------------------------------ #
    #  Consultas
    # ------------------------------------------------------------------ #
    def estudiante(self, cedula: str) -> Estudiante | None:
        return self.estudiantes.get(_str(cedula))

    def inscripciones(self, cedula: str) -> list[Inscripcion]:
        return self.ins.get(_str(cedula), [])

    def uc_de(self, codigo: str) -> UC | None:
        return self.ufo.get(_str(codigo))

    def unidades_credito(self, codigo: str) -> int:
        uc = self.uc_de(codigo)
        return uc.uc if uc else 0

    def es_proyecto(self, codigo: str) -> bool:
        uc = self.uc_de(codigo)
        return bool(uc and uc.tipo == "P")

    # --- Secciones / oferta ------------------------------------------- #
    def secciones_de(self, codigo: str) -> list[Seccion]:
        return self.secciones_por_uc.get(_str(codigo), [])

    def seccion(self, codigo: str, turno: str, seccion: str,
                periodo: str) -> Seccion | None:
        return self.secciones.get((_str(codigo), _str(turno),
                                   _str(seccion), _str(periodo)))

    def secciones_periodo(self, periodo: str) -> list[Seccion]:
        return [s for s in self.secciones.values() if s.periodo == _str(periodo)]

    def periodos_disponibles(self) -> list[str]:
        """Periodos (ej. '2019', '2019P') con oferta o inscripciones."""
        per = {s.periodo for s in self.secciones.values()}
        per |= {i.periodo for lst in self.ins.values() for i in lst}
        return sorted(per)

    def resumen(self) -> dict[str, Any]:
        return {
            "sede": self.sede.nombre,
            "clave": self.sede.clave,
            "data_dir": self.sede.data_dir,
            "estudiantes": len(self.estudiantes),
            "unidades": len(self.ufo),
            "pnf": len(self.pnf),
            "docentes": len(self.docentes),
            "periodos": len(self.periodos),
            "inscripciones": sum(len(v) for v in self.ins.values()),
            "secciones": len(self.secciones),
            "uc_sin_catalogo": len(self.faltantes_uc),
            "advertencias": list(self.advertencias),
        }
