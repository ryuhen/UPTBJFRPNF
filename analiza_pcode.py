# -*- coding: utf-8 -*-
"""
Localiza y analiza los bloques de p-code de Harbour dentro de pnf.exe.

Estrategia: en un EXE Harbour las funciones HB_FUNC generan arrays
`static const HB_BYTE pcode[]` con sentinela LINE al inicio y ENDPROC al final.
Aqui buscamos secuencias verosimiles de p-code y las describimos con el
descriptor oficial (doc/pcode.txt): opcode, operandos y textos embebidos.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

# Opcodes con operandos de tamano conocido (Harbour 3.x / pcode.txt)
# nombre: (bytes extra de operando)
OPCODES: dict[int, tuple[str, int]] = {
    0x00: ("ENDPROC", 0), 0x01: ("PUSHC", 2), 0x02: ("PUSHD", 8),
    0x03: ("PUSHNIL", 0), 0x04: ("PUSHNIL2", 0), 0x05: ("PUSHINT", 2),
    0x06: ("PUSHLONG", 4), 0x07: ("PUSHDBL", 8), 0x08: ("PUSHDATE", 8),
    0x09: ("PUSHP", 0), 0x0A: ("PUSHMARK", 0), 0x0B: ("PUSHUNMARK", 0),
    0x0C: ("PUSHCLIP", 0), 0x0D: ("PUSHCLIP32", 0), 0x0E: ("PUSHSHORT", 2),
    0x0F: ("PUSHBYTE", 1), 0x10: ("PUSHLEN", 0), 0x11: ("PUSHSTRLEN", 0),
    0x12: ("PUSHDEC", 0), 0x13: ("PUSHSYM", 2), 0x14: ("PUSHF", 2),
    0x15: ("PUSHCREF", 2), 0x16: ("PUSHMACRO", 2), 0x17: ("PUSHSELF", 0),
    0x18: ("PUSHGRE", 0), 0x19: ("PUSHGT", 0), 0x1A: ("PUSHGE", 0),
    0x1B: ("PUSHLT", 0), 0x1C: ("PUSHLE", 0), 0x1D: ("PUSHNE", 0),
    0x1E: ("JMP", 2), 0x1F: ("JMPFALSE", 2), 0x20: ("JMPTRUE", 2),
    0x21: ("AND", 0), 0x22: ("OR", 0), 0x23: ("NOT", 0),
    0x24: ("NEG", 0), 0x25: ("INC", 0), 0x26: ("DEC", 0),
    0x27: ("FUNCALL", 2), 0x28: ("DO", 2), 0x29: ("PUSH", 2),
    0x2A: ("LINE", 2), 0x2B: ("POP", 0), 0x2C: ("DUPL", 0),
    0x2D: ("SWAP", 0), 0x2E: ("NOP", 0), 0x2F: ("PUSHVP", 0),
    0x30: ("ZAP", 0), 0x31: ("DOEND", 0), 0x32: ("BOP", 2),
    0x33: ("FRAME", 2), 0x34: ("ENDFRAME", 2), 0x35: ("LOCAL", 2),
    0x36: ("STATIC", 2), 0x37: ("MEMVAR", 2), 0x38: ("FIELD", 2),
    0x39: ("STOREP", 0), 0x3A: ("STORE", 0), 0x3B: ("STOREFIELD", 0),
    0x3C: ("PUSHCLASSF", 2), 0x3D: ("PUSHOBJECT", 0),
    0x3E: ("NEWCLASS", 0), 0x3F: ("SENDS", 2), 0x40: ("SEND", 2),
    0x41: ("RETURN", 0), 0x42: ("URETURN", 0), 0x43: ("CLOSURE", 0),
    0x44: ("RUNDO", 0), 0x45: ("NUMCONV", 0), 0x46: ("STRCONV", 0),
    0x47: ("STRZERO", 0), 0x48: ("MACRO", 2), 0x49: ("MACROOBJ", 0),
    0x4A: ("MACROPUSH", 0), 0x4B: ("MACROFUNC", 2), 0x4C: ("MACRODO", 0),
    0x4D: ("MACROSEND", 0), 0x4E: ("EVAL", 0), 0x4F: ("EVALMAC", 0),
    0x50: ("WITH", 2), 0x51: ("ENDWITH", 0), 0x52: ("PUSHWA", 0),
    0x53: ("POPWA", 0), 0x54: ("FUNCALL", 0), 0x55: ("PARAM", 0),
    0x56: ("ENDPROC", 0),
}

_TEXT_RE = re.compile(rb"[\x20-\x7e]{6,}")


def scan(data: bytes, min_len: int = 12, limit: int = 40000) -> list[tuple[int, int, str]]:
    """Recorre el binario buscando cadenas de opcodes validos consecutivos."""
    hits = []
    i = 0
    n = len(data)
    while i < n and len(hits) < limit:
        start = i
        j = i
        steps = 0
        while j < n and steps < 4000:
            op = data[j]
            if op not in OPCODES:
                break
            _, extra = OPCODES[op]
            if j + 1 + extra > n:
                break
            j += 1 + extra
            steps += 1
        if steps >= min_len:
            hits.append((start, j, f"{steps} ops"))
            i = j
        else:
            i = start + 1
    return hits


def describe(data: bytes, start: int, end: int, max_ops: int = 250) -> str:
    out = []
    j = start
    ops = 0
    while j < end and ops < max_ops:
        op = data[j]
        name, extra = OPCODES.get(op, (f"?{op:02x}", 0))
        args = data[j + 1:j + 1 + extra]
        if op == 0x01 and extra == 2:  # PUSHC: string con longitud
            ln = args[1] << 8 | args[0] if len(args) == 2 else 0
            txt = data[j + 3:j + 3 + ln]
            out.append(f"{j:08x}  {name:<12} \"{txt.decode('latin-1')}\"")
            j += 3 + ln
            ops += 1
            continue
        if op == 0x13 and extra == 2:  # PUSHSYM: indice de simbolo
            idx = args[1] << 8 | args[0] if len(args) == 2 else 0
            out.append(f"{j:08x}  {name:<12} #{idx}")
        elif op == 0x2A and extra == 2:  # LINE
            ln = args[1] << 8 | args[0] if len(args) == 2 else 0
            out.append(f"{j:08x}  {name:<12} {ln}")
        else:
            out.append(f"{j:08x}  {name:<12} {args.hex()}")
        j += 1 + extra
        ops += 1
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: python analiza_pcode.py <pnf.exe>")
        return 2
    path = Path(sys.argv[1])
    data = path.read_bytes()
    print(f"Tamano: {len(data):,} bytes")
    hits = scan(data)
    print(f"Secuencias de p-code plausibles: {len(hits)}")
    total = sum(e - s for s, e, _ in hits)
    print(f"Bytes cubiertos: {total:,} ({total*100/len(data):.1f}%)")

    out_dir = path.parent / "_reversa"
    out_dir.mkdir(exist_ok=True)
    dest = out_dir / "pcode_hits.txt"
    with dest.open("w", encoding="utf-8") as fh:
        for s, e, info in hits:
            fh.write(f"=== 0x{s:08x} - 0x{e:08x}  ({info}, {e-s} bytes) ===\n")
            fh.write(describe(data, s, e, max_ops=400))
            fh.write("\n\n")
    print(f"Escrito: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
