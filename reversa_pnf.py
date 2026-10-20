# -*- coding: utf-8 -*-
"""
Ingenieria inversa estatica de pnf.exe (Harbour/MiniGUI).

El binario embebe el p-code de Harbour y, junto a el, tablas de simbolos en
claro: nombres de modulos .prg, procedimientos, funciones y objetos. Este
script reconstruye ese mapa sin ejecutar el binario.

Uso:
    python reversa_pnf.py C:\\SOCOPO\\pnf.exe
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Modulos de infraestructura (no son logica de negocio).
_INFRA = re.compile(r"^h_|^rdd|^tclass$|^tobject$|^hbv|^harb|^win_tole$|^objfunc$|^nconvert$")


def load_bytes(path: Path) -> bytes:
    return path.read_bytes()


def printable_strings(data: bytes, min_len: int = 4) -> list[tuple[int, str]]:
    """Cadenas ASCII imprimibles con su offset."""
    out: list[tuple[int, str]] = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data):
        out.append((m.start(), m.group().decode("latin-1")))
    return out


def harbour_symbols(data: bytes) -> list[str]:
    """Simbolos que Harbour deja en la tabla de la VM (nombres de proc/func)."""
    # Harbour usa identificadores en MAYUSCULAS para procedimientos/funciones
    # y PascalCase para clases/objetos. Filtramos basura y numeros.
    tokens = re.findall(rb"[A-Za-z_][A-Za-z0-9_]{2,40}", data)
    seen: dict[str, int] = {}
    for raw in tokens:
        tok = raw.decode("latin-1")
        seen[tok] = seen.get(tok, 0) + 1
    return [t for t, _ in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))]


def modules(data: bytes) -> list[str]:
    return sorted({m.group().decode("latin-1").lower() for m in re.finditer(rb"[A-Za-z0-9_\-]{2,40}\.prg", data)})


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: python reversa_pnf.py <ruta-pnf.exe>")
        return 2
    path = Path(sys.argv[1])
    data = load_bytes(path)

    mods = modules(data)
    business = [m for m in mods if not _INFRA.match(Path(m).stem)]
    infra = [m for m in mods if _INFRA.match(Path(m).stem)]

    print(f"# {path.name}  ({len(data):,} bytes)")
    print(f"# Modulos .prg embebidos: {len(mods)}")
    print()
    print("## Modulos de negocio")
    for m in business:
        print(f"  - {m}")
    print()
    print("## Infraestructura / framework (MiniGUI, RDD, OOP)")
    for m in infra:
        print(f"  - {m}")
    print()

    strings = printable_strings(data)
    syms = harbour_symbols(data)
    print(f"## Simbolos unicos: {len(syms)}")
    print(f"## Cadenas imprimibles: {len(strings)}")

    out_dir = path.parent / "_reversa"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "modules.txt").write_text("\n".join(mods), encoding="utf-8")
    (out_dir / "symbols.txt").write_text("\n".join(syms), encoding="utf-8")
    (out_dir / "strings.txt").write_text(
        "\n".join(f"{off:08x}\t{s}" for off, s in strings), encoding="utf-8"
    )
    proc_map = write_procedure_map(path)
    print(f"\nMapa de procedimientos: {proc_map}")
    print(f"Escrito en: {out_dir}")
    return 0


# --------------------------------------------------------------------------- #
#  Mapa de procedimientos por modulo
# --------------------------------------------------------------------------- #
# En el p-code de Harbour, a cada funcion le precede su nombre en la tabla de
# simbolos, en MAYUSCULAS, y a menudo tambien su nombre de origen PascalCase.
# Reconstruimos pares (modulo .prg -> procedimientos cercanos en el binario).
_PROC = re.compile(r"\b[A-Z][A-Z0-9_]{2,40}\b")
_NOT_PROC = {
    "TRUE", "FALSE", "NIL", "NULL", "IF", "ELSE", "ENDIF", "FOR", "NEXT",
    "WHILE", "ENDDO", "RETURN", "LOCAL", "STATIC", "PUBLIC", "PRIVATE",
    "FUNCTION", "PROCEDURE", "CLASS", "METHOD", "WITH", "ENDWITH", "SET",
    "USE", "SELECT", "INDEX", "DBF", "CDX", "PRG", "CH", "DLL", "EXE",
}


def procedures_by_module(path: Path) -> dict[str, list[str]]:
    """Procedimientos (mayusculas) hallados en la ventana de cada .prg."""
    data = path.read_bytes()
    mod_refs = [(m.start(), m.group().decode("latin-1").lower())
                for m in re.finditer(rb"[A-Za-z0-9_\-]{2,40}\.prg", data)]
    result: dict[str, list[str]] = {}
    for idx, (off, name) in enumerate(mod_refs):
        # Ventana: desde este .prg hasta el siguiente (max 64 KB).
        end = mod_refs[idx + 1][0] if idx + 1 < len(mod_refs) else off + 65536
        chunk = data[off:min(end, off + 65536)]
        procs: list[str] = []
        seen: set[str] = set()
        for m in _PROC.finditer(chunk.decode("latin-1")):
            tok = m.group()
            if tok in _NOT_PROC or tok in seen:
                continue
            # Evitamos nombres que son claramente strings de UI (con espacios
            # alrededor no aplica) y numeros puros.
            seen.add(tok)
            procs.append(tok)
        result[name] = procs
    return result


def write_procedure_map(path: Path) -> Path:
    out_dir = path.parent / "_reversa"
    out_dir.mkdir(exist_ok=True)
    mapping = procedures_by_module(path)
    dest = out_dir / "procedures_by_module.txt"
    lines: list[str] = []
    for mod in sorted(mapping):
        lines.append(f"=== {mod} ({len(mapping[mod])} simbolos) ===")
        for proc in mapping[mod]:
            lines.append(f"  {proc}")
        lines.append("")
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


if __name__ == "__main__":
    raise SystemExit(main())
