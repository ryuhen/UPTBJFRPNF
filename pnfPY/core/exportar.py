# -*- coding: utf-8 -*-
"""
pnfPY - Exportacion / empaquetado de los DBF de una sede.

Objetivo (pedido del usuario):
    Un coordinador de sede trabaja en su equipo con su propia carpeta DATA.
    Necesita ENVIAR esos datos al director. Para ello el programa debe:

      1. Copiar los DBF de la sede a una carpeta con el NOMBRE DE LA SEDE.
      2. Comprimir esa carpeta en un ZIP con el nombre de la sede
         (ej. `socopo.zip`).
      3. Dejar ese ZIP listo para enviar (correo/WhatsApp).

    Al recibirlo, el director coloca el ZIP en la carpeta `sedes\\` (o lo
    descomprime dentro) y ya puede trabajar esa sede junto con las demas.

Estructura generada:

    exportaciones\\
        socopo\\
            socopo\\DATA\\   <- copia de los DBF
        socopo.zip         <- el paquete a enviar
"""
from __future__ import annotations

import os
import shutil
import zipfile
from dataclasses import dataclass

from .sedes import Sede, _raiz_programa

RAIZ = _raiz_programa()
EXPORT_DIR = os.path.join(RAIZ, "exportaciones")

#: Patrones de archivo que forman la "base de datos" de una sede.
#: Se copian DBF y sus indices; se ignoran locks/temporales y adjuntos varios.
EXTENSIONES_DATOS = (".dbf", ".cdx", ".fpt", ".dbt", ".ntx")
PREFIJOS_IGNORAR = ("~$", ".~lock", "._")


def _es_dato(nombre: str) -> bool:
    low = nombre.lower()
    if any(low.startswith(p) for p in PREFIJOS_IGNORAR):
        return False
    return low.endswith(EXTENSIONES_DATOS)


@dataclass
class ResultadoExport:
    sede: str
    carpeta: str          # carpeta con los DBF copiados
    zip_path: str         # ruta del .zip generado
    n_archivos: int
    tamano_bytes: int


def exportar_sede(
    sede: Sede,
    destino: str | None = None,
    incluir_adjuntos: bool = False,
) -> ResultadoExport:
    """Copia los DBF de `sede` a `<destino>/<sede>` y los comprime en `<sede>.zip`.

    - `destino`: carpeta base de exportaciones (por defecto `pnfPY\\exportaciones`).
    - `incluir_adjuntos`: si True, copia tambien xlsx/csv/etc. (no recomendado,
      suele pesar mucho); por defecto solo copia los DBF/indices.

    Devuelve un `ResultadoExport` con las rutas y el conteo.
    """
    if not os.path.isdir(sede.data_dir):
        raise FileNotFoundError(f"La sede {sede.nombre} no tiene carpeta DATA: {sede.data_dir}")

    destino = destino or EXPORT_DIR
    nombre = sede.clave or sede.nombre.lower().replace(" ", "")

    # 1) Carpeta de trabajo: <destino>/<nombre>/<nombre>/DATA  (para que al
    #    descomprimir quede 'socopo/DATA/...' y se pueda copiar tal cual).
    carpeta_sede = os.path.join(destino, nombre)
    carpeta_data = os.path.join(carpeta_sede, "DATA")
    if os.path.isdir(carpeta_sede):
        shutil.rmtree(carpeta_sede, ignore_errors=True)
    os.makedirs(carpeta_data, exist_ok=True)

    # 2) Copiar los DBF
    n = 0
    for fn in os.listdir(sede.data_dir):
        origen = os.path.join(sede.data_dir, fn)
        if not os.path.isfile(origen):
            continue
        if not incluir_adjuntos and not _es_dato(fn):
            continue
        try:
            shutil.copy2(origen, os.path.join(carpeta_data, fn))
            n += 1
        except OSError:
            continue

    # 3) Comprimir en <destino>/<nombre>.zip
    zip_path = os.path.join(destino, f"{nombre}.zip")
    if os.path.isfile(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(carpeta_sede):
            for f in files:
                full = os.path.join(root, f)
                arc = os.path.relpath(full, destino)
                zf.write(full, arc)

    tam = os.path.getsize(zip_path) if os.path.isfile(zip_path) else 0
    return ResultadoExport(
        sede=sede.nombre, carpeta=carpeta_sede, zip_path=zip_path,
        n_archivos=n, tamano_bytes=tam,
    )


def exportar_todas(sedes: list[Sede], destino: str | None = None) -> list[ResultadoExport]:
    """Exporta y comprime cada sede de la lista."""
    out: list[ResultadoExport] = []
    for s in sedes:
        if not os.path.isdir(s.data_dir):
            continue
        out.append(exportar_sede(s, destino))
    return out


def instalar_desde_zip(zip_path: str, carpeta_sedes: str) -> Sede:
    """Instala un ZIP recibido (de una sede) dentro de `carpeta_sedes`.

    Extrae el contenido en `carpeta_sedes\\<nombre>`. Se espera que el ZIP
    contenga `<sede>/DATA/...` (como lo produce `exportar_sede`).

    Devuelve la `Sede` detectada.
    """
    from .sedes import _clave_sede, _nombre_bonito_desde_dir, es_data_dir

    base = os.path.splitext(os.path.basename(zip_path))[0]
    destino = os.path.join(carpeta_sedes, base)
    os.makedirs(destino, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(destino)

    # Buscar donde quedo la DATA (destino\DATA o destino\<sede>\DATA)
    candidatos = [destino, os.path.join(destino, base)]
    data_dir = None
    for c in candidatos:
        for nd in ("DATA", "data", "Data", ""):
            cand = os.path.join(c, nd) if nd else c
            if es_data_dir(cand):
                data_dir = cand
                break
        if data_dir:
            break

    if data_dir is None:
        # ultimo intento: buscar en profundidad
        for root, _d, _f in os.walk(destino):
            if es_data_dir(root):
                data_dir = root
                break

    if data_dir is None:
        raise FileNotFoundError(
            f"El ZIP {zip_path} no contiene una carpeta DATA valida (ALM/UFO/INS)."
        )

    nombre = _nombre_bonito_desde_dir(base)
    return Sede(
        clave=_clave_sede(nombre), nombre=nombre,
        raiz=destino, data_dir=data_dir, disponible=True,
    )
