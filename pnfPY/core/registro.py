# -*- coding: utf-8 -*-
"""
pnfPY - Registro multi-sede.

Mantiene cargadas SIMULTANEAMENTE las cuatro sedes (barinas, barinitas,
pedraza, socopo), cada una con su propio `DataStore`. Es la pieza que permite
"trabajar las cuatro sedes a la vez" eligiendo la sede activa sin reiniciar el
programa.

    reg = Registro()
    reg.cargar_todas()
    reg.sedes()                      # -> ['barinas', 'barinitas', ...]
    ds = reg.activa("barinas")       # DataStore de esa sede
    reg.cambiar("pedraza")           # cambia la sede activa
"""
from __future__ import annotations

from .data_store import DataStore
from .sedes import Sede, descubrir_sedes, resolver_entorno


class Registro:
    """Conjunto de sedes con sus datos, y una sede activa."""

    def __init__(self, sedes: list[Sede] | None = None, raiz: str | None = None):
        self._sedes: dict[str, Sede] = {}
        self._stores: dict[str, DataStore] = {}
        self._activa: str | None = None
        self.entorno = None

        if sedes is not None:
            lista = sedes
        else:
            # Detecta el entorno: carpeta `sedes\` (multi) o `DATA\` (simple).
            self.entorno = resolver_entorno(raiz)
            lista = self.entorno.sedes if self.entorno.sedes else descubrir_sedes()

        for s in lista:
            self._sedes[s.clave.lower()] = s

    # ------------------------------------------------------------------ #
    #  Inventario de sedes
    # ------------------------------------------------------------------ #
    def sedes(self) -> list[str]:
        """Claves de todas las sedes declaradas (en orden alfabetico)."""
        return sorted(self._sedes.keys())

    def sedes_disponibles(self) -> list[str]:
        """Claves de las sedes que tienen DATA valida."""
        return sorted(k for k, s in self._sedes.items() if s.disponible)

    def sede(self, clave: str) -> Sede | None:
        return self._sedes.get(clave.lower())

    # ------------------------------------------------------------------ #
    #  Carga
    # ------------------------------------------------------------------ #
    def cargar(self, clave: str, incluir_intersemestral: bool = True) -> DataStore:
        """Carga (o devuelve ya cargada) la sede indicada."""
        k = clave.lower()
        sede = self._sedes.get(k)
        if sede is None:
            raise KeyError(f"Sede desconocida: {clave}")
        if k not in self._stores:
            self._stores[k] = DataStore(sede).cargar(incluir_intersemestral)
        return self._stores[k]

    def cargar_todas(self, incluir_intersemestral: bool = True) -> "Registro":
        """Carga todas las sedes disponibles."""
        for k in self.sedes_disponibles():
            self.cargar(k, incluir_intersemestral)
        return self

    # ------------------------------------------------------------------ #
    #  Sede activa
    # ------------------------------------------------------------------ #
    def cambiar(self, clave: str, incluir_intersemestral: bool = True) -> DataStore:
        """Cambia la sede activa, cargandola si hace falta."""
        ds = self.cargar(clave, incluir_intersemestral)
        self._activa = clave.lower()
        return ds

    def activa(self, clave: str | None = None) -> DataStore:
        """Devuelve el DataStore de la sede activa (o el de `clave`)."""
        if clave is not None:
            return self.cargar(clave)
        if self._activa is None:
            disponibles = self.sedes_disponibles()
            if not disponibles:
                raise RuntimeError("No hay ninguna sede con datos disponibles.")
            self._activa = disponibles[0]
        return self.cargar(self._activa)

    @property
    def clave_activa(self) -> str | None:
        return self._activa

    def cargadas(self) -> list[str]:
        """Claves de las sedes ya cargadas en memoria."""
        return sorted(self._stores.keys())

    # ------------------------------------------------------------------ #
    #  Busqueda cruzada (opcional: util para reportes consolidados)
    # ------------------------------------------------------------------ #
    def buscar_estudiante(self, cedula: str) -> list[tuple[str, object]]:
        """Busca una cedula en TODAS las sedes cargadas.

        Devuelve [(clave_sede, Estudiante), ...] para las sedes donde exista.
        """
        ced = str(cedula).strip()
        out: list[tuple[str, object]] = []
        for k in self.cargadas():
            est = self._stores[k].estudiante(ced)
            if est is not None:
                out.append((k, est))
        return out

    def resumen(self) -> list[dict]:
        """Resumen de cada sede (cargadas o no)."""
        filas = []
        for k in self.sedes():
            sede = self._sedes[k]
            if k in self._stores:
                fila = self._stores[k].resumen()
                fila["cargada"] = True
                fila["disponible"] = True
                filas.append(fila)
            else:
                filas.append({
                    "sede": sede.nombre,
                    "clave": k,
                    "data_dir": sede.data_dir,
                    "disponible": sede.disponible,
                    "cargada": False,
                })
        return filas
