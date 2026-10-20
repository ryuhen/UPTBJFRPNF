# -*- coding: utf-8 -*-
"""
pnfPY - Historial academico y promedio ponderado.

Reutiliza la logica ya validada en `pnfNOTAS` (ver BITACORA_pnfNOTAS.md):

  * Nota minima aprobatoria: 12 general, 16 para el PROYECTO (UFO.TIPO = 'P').
  * Promedio ponderado = suma(nota x UC) / suma(UC).
  * La constancia muestra la ULTIMA nota por UC (la ultima aprobada si aprobo
    alguna vez).
  * Se agrupa por Trayecto y total del PNF.
  * Dos variantes de promedio: con y sin el ultimo anio inscrito.

Aqui se calcula sobre el `DataStore` de una sede.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .data_store import DataStore, Inscripcion

NOTA_MIN = 12
NOTA_MIN_PROYECTO = 16


# --------------------------------------------------------------------------- #
#  Estructuras de salida
# --------------------------------------------------------------------------- #
@dataclass
class UCItem:
    codigo: str
    nombre: str
    trayecto: str
    uc: int
    nota: float | None
    tipo: str
    carrera: str
    periodo: str
    aprobado: bool

    @property
    def ponderado(self) -> float:
        return (self.nota or 0) * self.uc


@dataclass
class Resumen:
    trayecto: str
    n_uc: int = 0
    total_uc: int = 0
    total_ponderado: float = 0.0

    @property
    def promedio(self) -> float:
        return round(self.total_ponderado / self.total_uc, 2) if self.total_uc else 0.0


@dataclass
class Historial:
    cedula: str
    estudiante: object | None
    carrera: str
    items: list[UCItem] = field(default_factory=list)
    por_trayecto: dict[str, Resumen] = field(default_factory=dict)
    total: Resumen = field(default_factory=lambda: Resumen(trayecto="TOTAL"))
    ultimo_anio: int | None = None


# --------------------------------------------------------------------------- #
#  Motor
# --------------------------------------------------------------------------- #
def _min_nota(ds: DataStore, codigo: str) -> int:
    return NOTA_MIN_PROYECTO if ds.es_proyecto(codigo) else NOTA_MIN


def _elegir_nota(inscripciones: list[Inscripcion], min_nota: int) -> Inscripcion:
    """Regla: ultima nota; si nunca aprobo, la ultima reprobada.

    `inscripciones` viene ordenada cronologicamente.
    """
    ultima = inscripciones[-1]
    aprobadas = [i for i in inscripciones if i.nota is not None and i.nota >= min_nota]
    if aprobadas:
        return aprobadas[-1]
    return ultima


def construir_historial(ds: DataStore, cedula: str) -> Historial:
    """Arma el historial de un estudiante en la sede `ds`."""
    ced = str(cedula).strip()
    est = ds.estudiante(ced)
    inscripciones = ds.inscripciones(ced)

    hist = Historial(cedula=ced, estudiante=est, carrera="")

    # Agrupar por codigo de UC
    por_codigo: dict[str, list[Inscripcion]] = {}
    for r in inscripciones:
        por_codigo.setdefault(r.codigo, []).append(r)

    conta_carrera: dict[str, int] = {}
    for codigo, lista in por_codigo.items():
        lista.sort(key=lambda i: i.orden)
        min_nota = _min_nota(ds, codigo)
        elegida = _elegir_nota(lista, min_nota)
        uc = ds.uc_de(codigo)
        item = UCItem(
            codigo=codigo,
            nombre=uc.nombre if uc else "",
            trayecto=(uc.trayecto if uc else elegida.trayecto) or elegida.trayecto,
            uc=(uc.uc if uc else elegida.uc),
            nota=elegida.nota,
            tipo=(uc.tipo if uc else elegida.tipo),
            carrera=elegida.carrera,
            periodo=elegida.periodo,
            aprobado=(elegida.nota is not None and elegida.nota >= min_nota),
        )
        hist.items.append(item)
        if elegida.carrera:
            conta_carrera[elegida.carrera] = conta_carrera.get(elegida.carrera, 0) + 1

    # Orden por trayecto y codigo
    hist.items.sort(key=lambda it: (_tray_key(it.trayecto), it.codigo))

    # Carrera / PNF mas frecuente
    if conta_carrera:
        hist.carrera = max(conta_carrera.items(), key=lambda kv: kv[1])[0]

    # Ultimo anio inscrito
    if inscripciones:
        hist.ultimo_anio = max(i.anio for i in inscripciones)

    # Agrupacion
    for it in hist.items:
        tray = it.trayecto or "0"
        res = hist.por_trayecto.setdefault(tray, Resumen(trayecto=tray))
        res.n_uc += 1
        res.total_uc += it.uc
        res.total_ponderado += it.ponderado
        hist.total.n_uc += 1
        hist.total.total_uc += it.uc
        hist.total.total_ponderado += it.ponderado

    return hist


def _tray_key(trayecto: str) -> int:
    try:
        return int(str(trayecto).strip())
    except (TypeError, ValueError):
        return 99


def historial_sin_ultimo_anio(hist: Historial) -> Resumen:
    """Promedio ponderado excluyendo el ultimo anio inscrito."""
    if hist.ultimo_anio is None:
        return hist.total
    res = Resumen(trayecto="TOTAL (sin ultimo anio)")
    for it in hist.items:
        anio = int("".join(ch for ch in it.periodo if ch.isdigit()) or 0)
        if anio == hist.ultimo_anio:
            continue
        res.n_uc += 1
        res.total_uc += it.uc
        res.total_ponderado += it.ponderado
    return res
