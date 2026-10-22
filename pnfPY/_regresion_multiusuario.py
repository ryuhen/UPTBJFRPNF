# -*- coding: utf-8 -*-
"""Prueba de regresion completa del flujo multiusuario (sobre COPIA de la sede)."""
import os
import shutil
import sys
import tempfile
import traceback

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from core import sedes as S
from core.data_store import DataStore
from core import multiusuario as MU
from core import dbf_reader
from core import inscripcion as INS

fallos = []


def check(nombre, cond, extra=""):
    print(("  OK   " if cond else "  FALLA") + f"  {nombre}" + (f"  {extra}" if extra else ""))
    if not cond:
        fallos.append(nombre)


def main():
    real = os.path.join(RAIZ, "datos", "socopo", "DATA")
    tmp = os.path.join(tempfile.gettempdir(), "pnf_regresion")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    data_dir = os.path.join(tmp, "datos", "socopo", "DATA")
    os.makedirs(os.path.dirname(data_dir))
    shutil.copytree(real, data_dir)

    S.RAIZ = tmp
    S.DATOS_DIR = os.path.join(tmp, "datos")
    sede = S.Sede("socopo", "Socopo", os.path.join(tmp, "datos", "socopo"), data_dir)

    ds = DataStore(sede).cargar()
    sec = ds.secciones_periodo("2024")[0]
    ins_path = sede.archivo("INS2024")
    n0 = MU._dbf_header_info(ins_path)[0]
    orig = dbf_reader.read_dbf(ins_path, keep_deleted=True)
    orig_ids = [(r["A_ID"], r["CODIGO"]) for r in orig.rows]

    print(f"\n[1] Base: INS2024 = {n0} registros, seccion {sec.codigo} {sec.turno}{sec.seccion}")

    # Pacientes sin esa UC
    cands = []
    for c in ds.estudiantes:
        if not any(i.codigo == sec.codigo and i.periodo == "2024" for i in ds.inscripciones(c)):
            cands.append(c)
        if len(cands) == 5:
            break

    # --- Dos usuarios, tandas distintas --------------------------------- #
    ta = MU.crear_tanda(sede, "Juan Perez", "2024")
    tb = MU.crear_tanda(sede, "Maria Gomez", "2024")
    print(f"\n[2] Tandas creadas: {ta.usuario} / {tb.usuario}")
    check("carpeta A aislada", os.path.isdir(ta.ruta))
    check("tanda A nace vacia", len(ta.inscripciones()) == 0)
    check("tanda no copia DBF", not any(f.upper().endswith(".DBF") for f in os.listdir(ta.ruta)))
    check("separada por usuario", ta.ruta != tb.ruta)

    uc = ds.uc_de(sec.codigo)
    def fila(c):
        return {"A_ID": c, "CARRERA": sec.pnf_codigo, "CODIGO": sec.codigo,
                "TRAYECTO": sec.trayecto, "TRAMO": sec.tramo, "TURNO": sec.turno,
                "SECCION": sec.seccion, "ANO": "2024", "CONDICION": "G",
                "TIPO": uc.tipo if uc else "", "UC": ds.unidades_credito(sec.codigo),
                "ESPECIAL": INS._especial(sec), "A_UNICA": INS._a_unica(c, sec)}

    for c in cands[:2]:
        ta.anotar_inscripcion(fila(c))
        ta.anotar_cupo(sec.ufo_clave, sec.turno, sec.seccion, "2024", +1)
    for c in (cands[0], cands[2]):     # uno repetido a proposito
        tb.anotar_inscripcion(fila(c))
        tb.anotar_cupo(sec.ufo_clave, sec.turno, sec.seccion, "2024", +1)

    print(f"\n[3] Anotado: A={len(ta.inscripciones())} B={len(tb.inscripciones())}")
    check("A anota 2", len(ta.inscripciones()) == 2)
    check("B anota 2", len(tb.inscripciones()) == 2)
    check("la sede NO se toco al anotar", MU._dbf_header_info(ins_path)[0] == n0)

    # --- Paquete con contrasena ---------------------------------------- #
    zp = MU.empaquetar(ta, password="secreta")
    print(f"\n[4] Paquete: {os.path.basename(zp)} ({os.path.getsize(zp)} bytes)")
    check("zip creado", os.path.isfile(zp))
    check("zip es pequeno (<50KB)", os.path.getsize(zp) < 50_000)
    try:
        import pyzipper  # noqa
        es_aes = True
    except ImportError:
        es_aes = False
    check("AES disponible" if es_aes else "ZIP normal (pyzipper no instalado)", True)

    rec = MU.extraer_paquete(zp, "secreta")
    check("paquete se descomprime", rec.usuario == "Juan Perez")
    check("contenido conservado", len(rec.inscripciones()) == 2)

    # --- Aplicar -------------------------------------------------------- #
    r1 = MU.aplicar_tanda(sede, rec)
    print(f"\n[5] Aplicar A: {r1.mensaje}")
    check("A agrega 2", r1.agregadas == 2 and r1.omitidas == 0)
    n1 = MU._dbf_header_info(ins_path)[0]
    check("INS crece exactamente +2", n1 == n0 + 2, f"{n0}->{n1}")

    r1b = MU.aplicar_tanda(sede, rec)
    print(f"[6] Re-aplicar A: {r1b.mensaje}")
    check("idempotente (no vuelve a aplicar)", not r1b.ok)
    check("no duplico al reaplicar", MU._dbf_header_info(ins_path)[0] == n1)

    r2 = MU.aplicar_tanda(sede, tb)
    print(f"[7] Aplicar B: {r2.mensaje}")
    check("B agrega 1 y omite 1", r2.agregadas == 1 and r2.omitidas == 1)
    print("     " + " | ".join(r2.detalle))

    n2 = MU._dbf_header_info(ins_path)[0]
    check("INS final +3", n2 == n0 + 3, f"{n0}->{n2}")

    # --- Integridad ----------------------------------------------------- #
    nuevo = dbf_reader.read_dbf(ins_path, keep_deleted=True)
    ids = [(r["A_ID"], r["CODIGO"]) for r in nuevo.rows]
    print(f"\n[8] Integridad: {len(ids)} filas leidas / {nuevo.n_records} en cabecera")
    check("cabecera coincide con filas", len(ids) == nuevo.n_records)
    check("TODOS los registros originales siguen", ids[:n0] == orig_ids)
    import collections
    dup_orig = {k for k, v in collections.Counter(orig_ids).items() if v > 1}
    dup_nuevos = {k for k, v in collections.Counter(ids).items() if v > 1} - dup_orig
    check("no hay duplicados NUEVOS cedula+UC", not dup_nuevos, str(dup_nuevos))
    if dup_orig:
        print(f"     (nota: {len(dup_orig)} pares ya venian duplicados en el DBF original)")

    # --- Contador INSCRITOS -------------------------------------------- #
    ds2 = DataStore(S.Sede("socopo", "Socopo", sede.raiz, data_dir)).cargar()
    s2 = ds2.seccion(sec.codigo, sec.turno, sec.seccion, "2024")
    real = MU._conteo_por_seccion(sede, "2024").get(
        (sec.ufo_clave.strip(), sec.turno, sec.seccion), 0)
    print(f"\n[9] INSCRITOS: {sec.inscritos} -> {s2.inscritos if s2 else '?'}"
          f"  (conteo real en INS2024 = {real})")
    check("contador coincide con el INS real", s2 is not None and s2.inscritos == real,
          f"SEA={s2.inscritos if s2 else '?'} vs INS={real}")
    check("contador subio (3 nuevas)", s2 is not None and s2.inscritos == sec.inscritos + 3,
          f"{sec.inscritos}->{s2.inscritos if s2 else '?'}")

    # --- Respaldos y trazabilidad -------------------------------------- #
    resp = os.path.join(data_dir, "_respaldos")
    mult = os.path.join(data_dir, "_multiusuario")
    nr = len([f for f in os.listdir(resp) if f.upper().endswith(".DBF")]) if os.path.isdir(resp) else 0
    print(f"\n[10] Respaldos={nr}  eventos={os.path.isfile(os.path.join(mult, 'eventos.log'))}")
    check("hay respaldos", nr >= 3)
    check("hay eventos.log", os.path.isfile(os.path.join(mult, "eventos.log")))
    check("hay aplicados.json", os.path.isfile(os.path.join(mult, "aplicados.json")))

    ap = MU._leer_json(os.path.join(mult, "aplicados.json"), [])
    check("2 tandas registradas", len(ap) == 2)
    check("cada una con huella", all("huella" in a for a in ap))

    # --- anulacion ------------------------------------------------------ #
    ta.anotar_anulacion(cands[1], sec.codigo, "2024")
    ra = MU.aplicar_tanda(sede, ta)
    print(f"\n[11] Anular via tanda: {ra.mensaje}")
    vivas = [f for f in dbf_reader.read_dbf(ins_path).rows
             if f["A_ID"] == cands[1] and f["CODIGO"] == sec.codigo]
    check("anulacion aplicada (borrado logico)", len(vivas) == 0)
    check("anulacion no borro filas", MU._dbf_header_info(ins_path)[0] == n2)

    # --- resumen -------------------------------------------------------- #
    r = MU.resumen_multiusuario(sede)
    print(f"\n[12] Resumen: aplicadas={len(r['aplicadas'])} respaldos={r['respaldos']}")
    check("resumen coherente", len(r["aplicadas"]) == 3)

    print("\n" + "=" * 60)
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones: {fallos}")
        return 1
    print("TODAS LAS COMPROBACIONES PASARON")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
