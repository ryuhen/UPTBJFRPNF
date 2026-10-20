# -*- coding: utf-8 -*-
r"""
pnfPY - Gestor de SEDES.

El sistema legado "Sistema Juan" (pnf.exe) asume que la carpeta DATA\
esta en la MISMA carpeta que el ejecutable (ej. C:\\SOCOPO\\pnf.exe +
C:\\SOCOPO\\DATA\\). Es decir, un coordinador = un equipo = una sede.

Aqui cambiamos eso: en vez de una sola sede, el programa ve VARIAS carpetas,
una por sede, cada una con su propia carpeta DATA\\ con la MISMA estructura
de archivos (ALM.DBF, UFO.DBF, INS####.DBF, CONFIG.DBF, ...). Asi un mismo
coordinador puede trabajar las cuatro sedes a la vez eligiendo la sede.

Estructura esperada:

    pnfPY\\
        datos\\
            barinas\\DATA\\
                ALM.DBF
                UFO.DBF
                INS2019.dbf
                ...
            barinitas\\DATA\\
            pedraza\\DATA\\
            socopo\\DATA\\

El gestor descubre automaticamente las sedes disponibles (cualquier subcarpeta
de `datos` que contenga una carpeta DATA valida) y expone un objeto `Sede`
por cada una.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field

from . import dbf_reader

# --------------------------------------------------------------------------- #
#  Constantes
# --------------------------------------------------------------------------- #
#: Prefijo de archivos de inscripcion por periodo: INS####[IP].DBF
PERIOD_RE = re.compile(r"^INS(\d{4})([IP]?)\.dbf$", re.IGNORECASE)

#: Nombres de las sedes conocidas de la UPTJFR (para etiquetas bonitas).
SEDES_CONOCIDAS: dict[str, str] = {
    "socopo": "Socopo",
    "pedraza": "Pedraza",
    "barinas": "Barinas",
    "barinitas": "Barinitas",
}

def _raiz_programa() -> str:
    r"""Carpeta base del programa (donde estan `datos\` y `datos_institucionales\`).

    * En desarrollo: la carpeta que contiene `pnf2.py` (...\pnfPY).
    * Empaquetado con PyInstaller (frozen): la carpeta donde esta el .EXE,
      para que el ejecutable lea su `datos\` de al lado, igual que el legado.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


RAIZ = _raiz_programa()                     # ...\pnfPY  o  carpeta del .exe
DATOS_DIR = os.path.join(RAIZ, "datos")     # ...\datos

#: Nombre de la carpeta que agrupa varias sedes (nueva convencion).
CARPETA_SEDES = "sedes"
#: Nombre de la carpeta de datos de una sola sede (convencion del legado).
CARPETA_DATA = "DATA"

#: Archivo de configuracion donde el coordinador declara su sede cuando el
#: programa corre en modo "una sola DATA" (junto al programa).
ARCHIVO_SEDE_LOCAL = "sede.local.json"


# --------------------------------------------------------------------------- #
#  Estructuras
# --------------------------------------------------------------------------- #
@dataclass
class Sede:
    """Una sede con su carpeta de datos DBF del sistema legado."""

    clave: str                       # identificador corto (sin espacios)
    nombre: str                      # etiqueta legible
    raiz: str                        # ...\datos\<clave>
    data_dir: str                    # ...\datos\<clave>\DATA
    disponible: bool = True

    # Cache de catalogos cargados (se llena bajo demanda via `cargar_basicos`)
    config: dict = field(default_factory=dict)
    _alm: object | None = None
    _ufo: object | None = None
    _pnf: object | None = None

    # ------------------------------------------------------------------ #
    def archivo(self, base: str) -> str | None:
        """Ruta a un DBF por nombre base (case-insensitive) dentro de DATA."""
        return dbf_reader.find_dbf(self.data_dir, base)

    def periodos(self) -> list[tuple[int, str, str]]:
        """Lista ordenada de (anio, sufijo, ruta) de los INS####[IP].DBF.

        sufijo: '' regular, 'I' intersemestral, 'P' PER.
        El orden es cronologico: anio ascendente y, dentro del mismo anio,
        regular < intersemestral < PER.
        """
        orden_suf = {"": 0, "I": 1, "P": 2}
        out: list[tuple[int, str, str]] = []
        if not os.path.isdir(self.data_dir):
            return out
        for fn in os.listdir(self.data_dir):
            m = PERIOD_RE.match(fn)
            if not m:
                continue
            anio = int(m.group(1))
            suf = m.group(2).upper()
            out.append((anio, suf, os.path.join(self.data_dir, fn)))
        out.sort(key=lambda t: (t[0], orden_suf.get(t[1], 9)))
        return out

    # ------------------------------------------------------------------ #
    def existe_data(self) -> bool:
        if not os.path.isdir(self.data_dir):
            return False
        nombres = {f.upper() for f in os.listdir(self.data_dir)}
        tiene_alm = "ALM.DBF" in nombres
        tiene_ufo = "UFO.DBF" in nombres
        tiene_ins = any(PERIOD_RE.match(n) for n in nombres)
        return tiene_alm and tiene_ufo and tiene_ins

    def resumen(self) -> str:
        """Texto corto de estado para mostrar en la GUI/CLI."""
        if not self.disponible:
            return f"{self.nombre}: (sin DATA)"
        n_ins = len(self.periodos())
        return f"{self.nombre}: {n_ins} periodos INS, DATA={self.data_dir}"


# --------------------------------------------------------------------------- #
#  Descubrimiento de sedes
# --------------------------------------------------------------------------- #
def _nombre_bonito(clave: str) -> str:
    return SEDES_CONOCIDAS.get(clave.lower(), clave.capitalize())


def descubrir_sedes(datos_dir: str | None = None) -> list[Sede]:
    """Recorre `datos\\` y devuelve una `Sede` por cada subcarpeta con DATA.

    Acepta que la carpeta DATA se llame DATA, data o Data.
    """
    datos_dir = datos_dir or DATOS_DIR
    sedes: list[Sede] = []
    if not os.path.isdir(datos_dir):
        return sedes

    for clave in sorted(os.listdir(datos_dir)):
        raiz_sede = os.path.join(datos_dir, clave)
        if not os.path.isdir(raiz_sede):
            continue

        data_dir = None
        for nombre in ("DATA", "data", "Data"):
            cand = os.path.join(raiz_sede, nombre)
            if os.path.isdir(cand):
                data_dir = cand
                break

        if data_dir is None:
            # sede declarada pero sin carpeta DATA todavia
            sedes.append(Sede(
                clave=clave, nombre=_nombre_bonito(clave),
                raiz=raiz_sede, data_dir=os.path.join(raiz_sede, "DATA"),
                disponible=False,
            ))
            continue

        s = Sede(
            clave=clave, nombre=_nombre_bonito(clave),
            raiz=raiz_sede, data_dir=data_dir,
        )
        s.disponible = s.existe_data()
        sedes.append(s)

    return sedes


def obtener_sede(clave: str, datos_dir: str | None = None) -> Sede | None:
    """Devuelve la sede por clave (case-insensitive) o None."""
    for s in descubrir_sedes(datos_dir):
        if s.clave.lower() == clave.lower():
            return s
    return None


# --------------------------------------------------------------------------- #
#  Deteccion de entorno: multi-sede (carpeta 'sedes') vs una sola 'DATA'
# --------------------------------------------------------------------------- #
def _nombre_bonito_desde_dir(nombre: str) -> str:
    """Deriva una clave/nombre de sede a partir del nombre de la carpeta.

    Acepta cosas como 'DATA SOCOPO', 'DataSocopo', 'socopo_data', 'SOCOPO'.
    Si no se reconoce una sede conocida, se usa el propio nombre saneado.
    """
    base = nombre.strip().lower()
    # quitar palabras genericas
    for ruido in ("data", "dbf", "_data", "_dbf", "datos"):
        base = base.replace(ruido, " ")
    tokens = [t for t in re.split(r"[\s_\-]+", base) if t]
    for t in tokens:
        if t in SEDES_CONOCIDAS:
            return SEDES_CONOCIDAS[t]
    limpio = " ".join(tokens).strip() or nombre.strip()
    return limpio.title()


def _clave_sede(nombre: str) -> str:
    """Convierte un nombre de sede en clave corta (sin espacios)."""
    return re.sub(r"[^a-z0-9]+", "", nombre.lower()) or "sede"


def es_data_dir(path: str) -> bool:
    """True si `path` contiene ALM.DBF, UFO.DBF y al menos un INS####."""
    if not os.path.isdir(path):
        return False
    try:
        nombres = {f.upper() for f in os.listdir(path)}
    except OSError:
        return False
    tiene_alm = "ALM.DBF" in nombres
    tiene_ufo = "UFO.DBF" in nombres
    tiene_ins = any(PERIOD_RE.match(n) for n in nombres)
    return tiene_alm and tiene_ufo and tiene_ins


@dataclass
class Entorno:
    r"""Resultado de la deteccion del entorno de trabajo.

    modo:
      'multi'  -> existe una carpeta `sedes\` con subcarpetas por sede.
      'simple' -> existe una unica carpeta `DATA\`; hay que declarar la sede.
      'vacio'  -> no se encontro ninguna estructura de datos.
    """

    modo: str
    sedes: list[Sede] = field(default_factory=list)
    data_dir_simple: str | None = None
    raiz_detectada: str | None = None
    mensaje: str = ""


def _sedes_desde_carpeta(carpeta_sedes: str) -> list[Sede]:
    """Construye una `Sede` por cada subcarpeta de `carpeta_sedes`.

    Cada subcarpeta puede contener la DATA directamente o una subcarpeta
    DATA/data. Ademas, si el nombre de la subcarpeta es 'DATA <SEDE>' o
    similar, se deduce el nombre de la sede.
    """
    sedes: list[Sede] = []
    if not os.path.isdir(carpeta_sedes):
        return sedes

    for entrada in sorted(os.listdir(carpeta_sedes)):
        raiz = os.path.join(carpeta_sedes, entrada)
        if not os.path.isdir(raiz):
            continue

        # Caso A: la propia subcarpeta ya es una DATA (contiene ALM/UFO/INS)
        if es_data_dir(raiz):
            nombre = _nombre_bonito_desde_dir(entrada)
            sedes.append(Sede(
                clave=_clave_sede(nombre), nombre=nombre,
                raiz=raiz, data_dir=raiz, disponible=True,
            ))
            continue

        # Caso B: la subcarpeta contiene una carpeta DATA/data/Data
        data_dir = None
        for nombre_data in ("DATA", "data", "Data"):
            cand = os.path.join(raiz, nombre_data)
            if os.path.isdir(cand):
                data_dir = cand
                break
        if data_dir is None:
            continue

        # El nombre de la sede sale del nombre de la subcarpeta; si no, de DATA
        nombre = _nombre_bonito_desde_dir(entrada)
        if nombre.lower() in ("data", "datos", ""):
            nombre = _nombre_bonito_desde_dir(os.path.basename(raiz))
        s = Sede(
            clave=_clave_sede(nombre), nombre=nombre,
            raiz=raiz, data_dir=data_dir,
        )
        s.disponible = s.existe_data()
        sedes.append(s)

    return sedes


def _cargar_sede_local(raiz: str) -> str | None:
    """Lee `sede.local.json` (sede declarada por el coordinador) si existe."""
    import json
    ruta = os.path.join(raiz, ARCHIVO_SEDE_LOCAL)
    if not os.path.isfile(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("sede") or data.get("nombre") or data.get("clave")
    except (OSError, ValueError):
        return None


def guardar_sede_local(nombre: str, raiz: str | None = None) -> str:
    """Guarda en `sede.local.json` el nombre de sede declarado por el usuario."""
    import json
    raiz = raiz or RAIZ
    ruta = os.path.join(raiz, ARCHIVO_SEDE_LOCAL)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump({"sede": nombre}, fh, ensure_ascii=False, indent=2)
    return ruta


def resolver_entorno(raiz: str | None = None) -> Entorno:
    r"""Detecta como estan organizados los datos.

    Reglas (en orden):
      1. Si existe una carpeta `sedes\` (o `datos\`) con subcarpetas por sede
         -> modo 'multi': se ofrece la seleccion de sede.
      2. Si no, si existe una carpeta `DATA\` junto al programa
         -> modo 'simple': se trabaja con esa DATA y se pide al coordinador que
            indique a que sede pertenece (se recuerda en `sede.local.json`).
      3. Si no hay nada -> modo 'vacio'.
    """
    raiz = raiz or RAIZ

    # 1) Carpeta 'sedes' (nueva convencion) o 'datos' (la que usamos aqui)
    for nombre in (CARPETA_SEDES, "datos"):
        cand = os.path.join(raiz, nombre)
        if os.path.isdir(cand):
            sedes = _sedes_desde_carpeta(cand)
            if sedes:
                return Entorno(
                    modo="multi", sedes=sedes, raiz_detectada=cand,
                    mensaje=f"Modo multi-sede: {len(sedes)} sede(s) en {cand}",
                )

    # 2) Carpeta DATA unica (convencion del legado: pnf.exe junto a DATA)
    for nombre in (CARPETA_DATA, "data", "Data"):
        cand = os.path.join(raiz, nombre)
        if es_data_dir(cand):
            declarada = _cargar_sede_local(raiz)
            nombre_sede = declarada or _nombre_bonito_desde_dir(os.path.basename(raiz))
            s = Sede(
                clave=_clave_sede(nombre_sede), nombre=nombre_sede,
                raiz=raiz, data_dir=cand, disponible=True,
            )
            msg = (f"Modo una sola sede: DATA en {cand}. "
                   f"Sede declarada: {nombre_sede}")
            if not declarada:
                msg += " (sin declarar; el coordinador debe indicarla)"
            return Entorno(
                modo="simple", sedes=[s], data_dir_simple=cand,
                raiz_detectada=raiz, mensaje=msg,
            )

    # 3) Nada
    return Entorno(modo="vacio",
                   mensaje=f"No se encontro carpeta DATA ni sedes en {raiz}")
