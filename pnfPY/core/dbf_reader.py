# -*- coding: utf-8 -*-
"""
pnfNOTAS - Lector de archivos DBF (dBase III/IV / FoxPro) sin dependencias.

Lee la cabecera, los descriptores de campos y los registros de un archivo .dbf.
No usa dbfread ni pandas: todo se hace a mano para que el visor sea portable.

Soporta los tipos de campo usados por el sistema legado "Sistema Juan":
    C -> texto (latin-1)
    N/F -> numero (entero o decimal)
    L -> logico (T/Y -> True, F/N -> False)
    D -> fecha (AAAAMMDD -> 'AAAA-MM-DD')
    M/G -> memo (se deja vacio; el contenido esta en el .fpt/.dbt)
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator


# --------------------------------------------------------------------------- #
#  Estructuras
# --------------------------------------------------------------------------- #
@dataclass
class DbfField:
    name: str
    type: str
    length: int
    decimals: int
    offset: int


@dataclass
class DbfTable:
    path: str
    name: str
    n_records: int
    header_len: int
    record_len: int
    fields: list[DbfField]
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]

    def get_field(self, name: str) -> DbfField | None:
        up = name.upper()
        for f in self.fields:
            if f.name.upper() == up:
                return f
        return None

    def __len__(self) -> int:
        return len(self.rows)


# --------------------------------------------------------------------------- #
#  Lector
# --------------------------------------------------------------------------- #
def _decode(raw: bytes, ftype: str) -> Any:
    txt = raw.decode("latin-1").strip()
    if ftype in ("N", "F", "B", "I", "O"):
        if txt == "":
            return None
        try:
            if "." in txt:
                return float(txt)
            return int(txt)
        except ValueError:
            try:
                return float(txt)
            except ValueError:
                return None
    if ftype == "L":
        return txt in ("T", "Y", "t", "y")
    if ftype == "D":
        if len(txt) == 8 and txt.isdigit():
            return f"{txt[0:4]}-{txt[4:6]}-{txt[6:8]}"
        return txt or None
    # C, M, G, etc. -> texto
    return txt


def read_dbf(path: str, keep_deleted: bool = False, fields: set[str] | None = None) -> DbfTable:
    """Lee un archivo DBF completo y devuelve una DbfTable.

    `fields`: si se indica (nombres en mayuscula), solo se decodifican esas
    columnas.  Acelera mucho las tablas grandes (INS####) donde solo se
    necesitan unas pocas columnas.
    """
    wanted = {f.upper() for f in fields} if fields else None
    with open(path, "rb") as fh:
        header = fh.read(32)
        if len(header) < 32:
            raise ValueError(f"{path}: cabecera DBF invalida (muy corta)")

        n_records = struct.unpack("<I", header[4:8])[0]
        header_len = struct.unpack("<H", header[8:10])[0]
        record_len = struct.unpack("<H", header[10:12])[0]

        # Descriptores de campo: 32 bytes c/u, hasta el terminador 0x0D.
        fh.seek(32)
        fields: list[DbfField] = []
        offset = 1  # el byte 0 de cada registro es la bandera de borrado
        while True:
            b = fh.read(1)
            if b in (b"\r", b"\x0d", b""):
                break
            desc = b + fh.read(31)
            if len(desc) < 32:
                break
            name = desc[0:11].split(b"\x00")[0].decode("latin-1").strip()
            ftype = chr(desc[11])
            flen = desc[16]
            fdec = desc[17]
            fields.append(DbfField(name, ftype, flen, fdec, offset))
            offset += flen

        fh.seek(header_len)
        rows: list[dict[str, Any]] = []
        for _ in range(n_records):
            rec = fh.read(record_len)
            if len(rec) < record_len:
                break
            deleted = rec[0:1] == b"*"
            if deleted and not keep_deleted:
                continue
            row: dict[str, Any] = {}
            for fld in fields:
                if wanted is not None and fld.name.upper() not in wanted:
                    continue
                raw = rec[fld.offset:fld.offset + fld.length]
                row[fld.name] = _decode(raw, fld.type)
            if deleted:
                row["_DELETED"] = True
            rows.append(row)

    return DbfTable(
        path=path,
        name=os.path.splitext(os.path.basename(path))[0].upper(),
        n_records=n_records,
        header_len=header_len,
        record_len=record_len,
        fields=fields,
        rows=rows,
    )


def find_dbf(data_dir: str, base: str) -> str | None:
    """Busca un DBF por nombre base (case-insensitive) en un directorio."""
    if not os.path.isdir(data_dir):
        return None
    want = base.lower()
    for fn in os.listdir(data_dir):
        if fn.lower() == want + ".dbf":
            return os.path.join(data_dir, fn)
    return None


def iter_year_dbfs(data_dir: str, prefix: str) -> Iterator[tuple[int, str]]:
    """Itera los DBF tipo INS2009.DBF / SEA2013.DBF devolviendo (año, ruta)."""
    if not os.path.isdir(data_dir):
        return
    for fn in os.listdir(data_dir):
        low = fn.lower()
        if not low.startswith(prefix.lower()) or not low.endswith(".dbf"):
            continue
        stem = fn[: -4]
        year = "".join(ch for ch in stem if ch.isdigit())
        if len(year) >= 4:
            yield int(year[:4]), os.path.join(data_dir, fn)