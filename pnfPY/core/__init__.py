# -*- coding: utf-8 -*-
"""
pnfPY - nucleo del sistema (lectura DBF multi-sede).

Modulos:
    dbf_reader   - lector de DBF sin dependencias.
    sedes        - descubrimiento y gestion de las sedes (carpetas).
    data_store   - carga e indice de los datos de una sede.
    registro     - registro multi-sede (las cuatro sedes a la vez).
    historial    - historial academico y promedio ponderado.
"""
from .sedes import (
    Sede, descubrir_sedes, obtener_sede, resolver_entorno, Entorno,
    guardar_sede_local, es_data_dir,
)
from .data_store import DataStore, Estudiante, Inscripcion, UC, Seccion
from .registro import Registro
from .exportar import (
    exportar_sede, exportar_todas, instalar_desde_zip, ResultadoExport,
)
from . import inscripcion
from . import carga_notas

__all__ = [
    "Sede", "descubrir_sedes", "obtener_sede",
    "resolver_entorno", "Entorno", "guardar_sede_local", "es_data_dir",
    "DataStore", "Estudiante", "Inscripcion", "UC", "Seccion",
    "Registro",
    "exportar_sede", "exportar_todas", "instalar_desde_zip", "ResultadoExport",
    "inscripcion", "carga_notas",
]
