# -*- coding: utf-8 -*-
"""
pnfPY - Sistema academico UPTJFR (reimplementacion en Python del legado pnf.exe).

Reescritura del sistema "Sistema Juan" (Harbour/HMG, `pnf.exe`) en Python, con
una diferencia clave: trabaja VARIAS SEDES a la vez mediante carpetas.

    pnfPY\\datos\\barinas\\DATA\\
    pnfPY\\datos\\barinitas\\DATA\\
    pnfPY\\datos\\pedraza\\DATA\\
    pnfPY\\datos\\socopo\\DATA\\

Uso rapido (CLI):

    python pnf2.py sedes                         # lista las sedes detectadas
    python pnf2.py estado --sede socopo          # resumen de una sede
    python pnf2.py buscar 25079140 --sede socopo # datos de un estudiante
    python pnf2.py historial 25079140 --sede socopo

Sin argumentos abre la GUI (Tkinter) con un selector de sede.

Los modulos funcionales (inscripcion, carga academica, notas, grado,
constancias) se van anadiendo sobre este nucleo multi-sede.
"""
from __future__ import annotations

import argparse
import os
import sys

from core import Registro, descubrir_sedes, resolver_entorno
from core import exportar as EXP
from core import inscripcion as INS
from core import carga_notas as CN
from core import historial as H


# --------------------------------------------------------------------------- #
#  Utilidades de consola
# --------------------------------------------------------------------------- #
def _print_sedes(reg: Registro) -> None:
    if reg.entorno is not None:
        print(f"MODO: {reg.entorno.modo.upper()} - {reg.entorno.mensaje}")
        print("-" * 60)
    print("SEDES DETECTADAS")
    print("-" * 60)
    for fila in reg.resumen():
        if fila.get("cargada"):
            print(f"  [{fila['clave']:>10}] {fila['sede']:<12} "
                  f"{fila['estudiantes']:>6} estudiantes, "
                  f"{fila['unidades']:>4} UC, {fila['periodos']:>2} periodos")
        else:
            estado = "con datos" if fila.get("disponible") else "SIN DATA"
            print(f"  [{fila['clave']:>10}] {fila['sede']:<12} {estado}")
    print("-" * 60)
    for s in descubrir_sedes():
        print(f"  {s.clave:<10} -> {s.data_dir}")


def _cmd_entorno(args: argparse.Namespace) -> int:
    """Muestra como detecta el programa la organizacion de los datos."""
    ent = resolver_entorno()
    print(f"MODO: {ent.modo}")
    print(f"  {ent.mensaje}")
    if ent.modo == "multi":
        print("  Sedes detectadas:")
        for s in ent.sedes:
            print(f"    - {s.clave:<10} {s.nombre:<12} DATA={s.data_dir}")
        print("  -> El programa ofrecera una SELECCION de sede.")
    elif ent.modo == "simple":
        print(f"  DATA unica: {ent.data_dir_simple}")
        print("  -> El programa trabajara con esa DATA y pedira al coordinador")
        print("     que indique a que sede pertenece (se guarda en sede.local.json).")
    else:
        print("  -> No se encontro estructura de datos.")
    return 0


def _cmd_sedes(args: argparse.Namespace) -> int:
    reg = Registro()
    reg.cargar_todas()
    _print_sedes(reg)
    return 0


def _cmd_estado(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    r = ds.resumen()
    print(f"SEDE: {r['sede']} ({r['clave']})")
    print(f"  DATA        : {r['data_dir']}")
    print(f"  Estudiantes : {r['estudiantes']}")
    print(f"  Unidades UC : {r['unidades']}")
    print(f"  PNF         : {r['pnf']}")
    print(f"  Docentes    : {r['docentes']}")
    print(f"  Periodos INS: {r['periodos']}")
    print(f"  Inscripciones: {r['inscripciones']}")
    print(f"  UC sin catalogo: {r['uc_sin_catalogo']}")
    if r["advertencias"]:
        print("  Advertencias:")
        for a in r["advertencias"]:
            print(f"    - {a}")
    return 0


def _cmd_buscar(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    est = ds.estudiante(args.cedula)
    if est is None:
        print(f"No se encontro la cedula {args.cedula} en {ds.sede.nombre}.")
        return 1
    print(f"Cedula    : {est.cedula}")
    print(f"Nombre    : {est.nombre_completo}")
    print(f"Ingreso   : {est.ingreso}")
    print(f"Telefono  : {est.telefono}")
    print(f"Inscripciones: {len(ds.inscripciones(est.cedula))}")
    return 0


def _cmd_historial(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    hist = H.construir_historial(ds, args.cedula)
    if not hist.items:
        print(f"Sin historial para {args.cedula} en {ds.sede.nombre}.")
        return 1

    print(f"CONSTANCIA DE NOTAS - {ds.sede.nombre}")
    if hist.estudiante is not None:
        print(f"Estudiante: {hist.estudiante.nombre_completo} "
              f"(C.I. {hist.estudiante.cedula})")
    print(f"Carrera   : {hist.carrera}")
    print("-" * 78)
    print(f"{'CODIGO':<14}{'UC':>3}{'NOTA':>6}{'UC-CR':>6}{'POND':>7}  NOMBRE")
    print("-" * 78)
    for it in hist.items:
        nota = "-" if it.nota is None else f"{it.nota:.0f}"
        print(f"{it.codigo:<14}{it.trayecto:>3}{nota:>6}{it.uc:>6}"
              f"{it.ponderado:>7.0f}  {it.nombre[:34]}")
    print("-" * 78)
    for tray in sorted(hist.por_trayecto):
        res = hist.por_trayecto[tray]
        print(f"Trayecto {tray}: {res.n_uc} UC, {res.total_uc} creditos, "
              f"promedio = {res.promedio}")
    print(f"TOTAL   : {hist.total.n_uc} UC, {hist.total.total_uc} creditos, "
          f"promedio = {hist.total.promedio}")
    sin_ult = H.historial_sin_ultimo_anio(hist)
    if sin_ult is not hist.total:
        print(f"Sin ultimo anio ({hist.ultimo_anio}): "
              f"promedio = {sin_ult.promedio}")
    return 0


def _cmd_exportar(args: argparse.Namespace) -> int:
    """Exporta los DBF de una (o todas) las sedes y los comprime en .zip."""
    reg = Registro()
    if args.sede and args.sede.lower() != "todas":
        sede = reg.sede(args.sede)
        if sede is None:
            print(f"Sede desconocida: {args.sede}")
            return 1
        sedes = [sede]
    else:
        sedes = [s for s in (reg.sede(k) for k in reg.sedes_disponibles()) if s]

    resultados = EXP.exportar_todas(sedes, args.destino)
    if not resultados:
        print("No se exporto ninguna sede (¿sin carpeta DATA?).")
        return 1
    print("EXPORTACION COMPLETADA")
    print("-" * 60)
    for r in resultados:
        mb = r.tamano_bytes / (1024 * 1024)
        print(f"  {r.sede:<12} {r.n_archivos:>4} DBF -> {r.zip_path}")
        print(f"  {'':<12} paquete: {mb:.1f} MB")
    print("-" * 60)
    print("Envie el/los .zip al director. El los coloca en la carpeta 'sedes'")
    print("o usa: python pnf2.py instalar <zip> --sedes <carpeta>")
    return 0


def _cmd_instalar(args: argparse.Namespace) -> int:
    """Instala un ZIP de sede recibido dentro de la carpeta de sedes."""
    from core.sedes import DATOS_DIR
    carpeta = args.sedes or DATOS_DIR
    os.makedirs(carpeta, exist_ok=True)
    sede = EXP.instalar_desde_zip(args.zip, carpeta)
    print(f"Sede instalada: {sede.nombre} ({sede.clave})")
    print(f"  DATA: {sede.data_dir}")
    print(f"  Valida: {sede.existe_data()}")
    return 0


# --- Inscripcion --------------------------------------------------------- #
def _cmd_oferta(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    secs = INS.oferta(ds, args.periodo, args.trayecto, args.pnf)
    print(f"OFERTA ACADEMICA - {ds.sede.nombre} - periodo {args.periodo}")
    print("-" * 90)
    print(f"{'CODIGO':<14}{'T':>2}{'TUR':>4}{'SEC':>4}{'CUPO':>6}{'INSC':>6}  NOMBRE / DOCENTE")
    print("-" * 90)
    for s in secs:
        print(f"{s.codigo:<14}{s.trayecto:>2}{s.turno:>4}{s.seccion:>4}"
              f"{s.cupo:>6}{s.inscritos:>6}  {s.nombre[:34]}")
        if s.docente:
            print(f"{'':<42}{s.docente[:40]}")
    print("-" * 90)
    print(f"Total secciones: {len(secs)}")
    return 0


def _cmd_inscritos(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    filas = INS.inscritos_por_uc(ds, args.codigo, args.periodo)
    uc = ds.uc_de(args.codigo)
    titulo = uc.nombre if uc else args.codigo
    print(f"INSCRITOS EN {args.codigo} - {titulo}")
    if args.periodo:
        print(f"Periodo: {args.periodo}")
    print("-" * 84)
    print(f"{'CEDULA':<14}{'T':>3}{'TUR':>4}{'SEC':>4}{'NOTA':>6}{'ASIS':>6}  ESTUDIANTE")
    print("-" * 84)
    for f in filas:
        nota = "-" if f["nota"] is None else f"{f['nota']:.0f}"
        asis = "-" if f["asistencia"] is None else f"{f['asistencia']:.0f}"
        print(f"{f['cedula']:<14}{f['trayecto']:>3}{f['turno']:>4}{f['seccion']:>4}"
              f"{nota:>6}{asis:>6}  {f['nombre'][:36]}")
    print("-" * 84)
    print(f"Total: {len(filas)}")
    return 0


def _cmd_inscripcion(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    lista = INS.inscripcion_de(ds, args.cedula, args.periodo)
    est = ds.estudiante(args.cedula)
    print(f"INSCRIPCION - {ds.sede.nombre}")
    if est:
        print(f"{est.nombre_completo} (C.I. {est.cedula})")
    if args.periodo:
        print(f"Periodo: {args.periodo}")
    print("-" * 84)
    print(f"{'CODIGO':<14}{'T':>3}{'TUR':>4}{'SEC':>4}{'NOTA':>6}{'PERIODO':>9}  UC")
    print("-" * 84)
    for i in lista:
        uc = ds.uc_de(i.codigo)
        nota = "-" if i.nota is None else f"{i.nota:.0f}"
        print(f"{i.codigo:<14}{i.trayecto:>3}{i.turno:>4}{i.seccion:>4}"
              f"{nota:>6}{i.periodo:>9}  {(uc.nombre if uc else '')[:32]}")
    print("-" * 84)
    print(f"Total UC: {len(lista)}")
    return 0


def _cmd_inscribir(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    sec = ds.seccion(args.codigo, args.turno, args.seccion, args.periodo)
    if sec is None:
        print("No se encontro esa seccion en la oferta. Revise codigo/turno/"
              "seccion/periodo con el comando 'oferta'.")
        return 1
    res = INS.inscribir(ds, args.cedula, sec, args.periodo, forzar=args.forzar)
    print("OK: " if res.ok else "RECHAZADO: ", res.mensaje)
    for d in res.detalle:
        print("  - " + d)
    return 0 if res.ok else 1


def _cmd_anular(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    res = INS.anular(ds, args.cedula, args.codigo, args.periodo)
    print("OK: " if res.ok else "RECHAZADO: ", res.mensaje)
    return 0 if res.ok else 1


# --- Carga de notas (planilla cifrada) y respaldos ----------------------- #
def _cmd_generar_carga(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    sec = ds.seccion(args.codigo, args.turno, args.seccion, args.periodo)
    if sec is None:
        print("No se encontro esa seccion. Revise con 'oferta'.")
        return 1
    res = CN.generar_planilla(ds, sec, destino=args.destino,
                              password_docente=args.password)
    print("OK:" if res.ok else "ERROR:", res.mensaje)
    if res.ruta:
        print(f"  Archivo: {res.ruta}")
        print("  CONTENEDOR CIFRADO CON LA CLAVE MAESTRA (capa 1): el sistema")
        print("  siempre puede reimportarlo. La clave del docente (capa 2) se")
        print("  entrega en el mensaje y queda en el archivo .llave.json.")
    return 0 if res.ok else 1


def _cmd_importar_carga(args: argparse.Namespace) -> int:
    reg = Registro()
    ds = reg.cargar(args.sede)
    res = CN.importar_planilla(ds, args.archivo, args.password, args.periodo,
                               previa=args.previa)
    print("OK:" if res.ok else "ERROR:", res.mensaje)
    if res.filas:
        print()
        print(f"{'CEDULA':<12}{'NOTA':>6}{'ANT':>6}{'ASIS':>6}  ESTADO / ESTUDIANTE")
        print("-" * 74)
        for f in res.filas:
            nota = "-" if f["nota"] is None else f"{f['nota']:.0f}"
            ant = "-" if f["nota_anterior"] in (None, "") else str(f["nota_anterior"])
            asis = "-" if f["asistencia"] is None else f"{f['asistencia']:.0f}"
            estado = "OK " if (f["encontrado"] and f["nota"] is not None) else "omite"
            print(f"{f['cedula']:<12}{nota:>6}{ant:>6}{asis:>6}  {estado:<5} {f['nombre'][:34]}")
        print("-" * 74)
        if res.previa:
            print("VISTA PREVIA: no se escribio nada. Repita el comando sin")
            print("--previa para cargar las notas.")
    return 0 if res.ok else 1


def _cmd_respaldar(args: argparse.Namespace) -> int:
    reg = Registro()
    sede = reg.sede(args.sede)
    if sede is None:
        print(f"Sede desconocida: {args.sede}")
        return 1
    res = CN.respaldar_sede(sede, args.password, args.destino)
    print("OK:" if res.ok else "ERROR:", res.mensaje)
    if res.ruta:
        print(f"  Archivo: {res.ruta}")
    return 0 if res.ok else 1


def _cmd_restaurar(args: argparse.Namespace) -> int:
    from core.sedes import DATOS_DIR
    res = CN.restaurar_respaldo(args.zip, args.password, args.destino or DATOS_DIR)
    print("OK:" if res.ok else "ERROR:", res.mensaje)
    return 0 if res.ok else 1


# --------------------------------------------------------------------------- #
#  GUI (selector de sede)
# --------------------------------------------------------------------------- #
def _gui() -> int:
    try:
        from gui import main as gui_main
    except ImportError as e:
        print(f"No se pudo abrir la GUI ({e}). Use los comandos CLI.")
        return 1
    return gui_main()


# --------------------------------------------------------------------------- #
#  Parser
# --------------------------------------------------------------------------- #
def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pnf",
        description="Sistema academico UPTJFR (Python, multi-sede).",
    )
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("sedes", help="Lista las sedes detectadas.")
    sp.set_defaults(func=_cmd_sedes)

    sp = sub.add_parser("entorno", help="Muestra como se detectan los datos.")
    sp.set_defaults(func=_cmd_entorno)

    sp = sub.add_parser("exportar",
                        help="Copia los DBF de una sede y los comprime en .zip.")
    sp.add_argument("--sede", default="todas",
                    help="Sede a exportar (por defecto: todas).")
    sp.add_argument("--destino", default=None,
                    help="Carpeta de destino (por defecto: pnfPY\\exportaciones).")
    sp.set_defaults(func=_cmd_exportar)

    sp = sub.add_parser("instalar", help="Instala un .zip de sede recibido.")
    sp.add_argument("zip")
    sp.add_argument("--sedes", default=None,
                    help="Carpeta de sedes donde instalar (por defecto: pnfPY\\datos).")
    sp.set_defaults(func=_cmd_instalar)

    # --- Inscripcion ----------------------------------------------------- #
    sp = sub.add_parser("oferta", help="Muestra la oferta academica de un periodo.")
    sp.add_argument("--sede", required=True)
    sp.add_argument("--periodo", required=True)
    sp.add_argument("--trayecto", default=None)
    sp.add_argument("--pnf", default=None)
    sp.set_defaults(func=_cmd_oferta)

    sp = sub.add_parser("inscritos", help="Estudiantes inscritos en una UC.")
    sp.add_argument("codigo")
    sp.add_argument("--sede", required=True)
    sp.add_argument("--periodo", default=None)
    sp.set_defaults(func=_cmd_inscritos)

    sp = sub.add_parser("inscripcion", help="Inscripciones de un estudiante.")
    sp.add_argument("cedula")
    sp.add_argument("--sede", required=True)
    sp.add_argument("--periodo", default=None)
    sp.set_defaults(func=_cmd_inscripcion)

    sp = sub.add_parser("inscribir", help="Inscribe a un estudiante en una seccion.")
    sp.add_argument("cedula")
    sp.add_argument("--sede", required=True)
    sp.add_argument("--codigo", required=True)
    sp.add_argument("--turno", required=True)
    sp.add_argument("--seccion", required=True)
    sp.add_argument("--periodo", required=True)
    sp.add_argument("--forzar", action="store_true",
                    help="Inscribe aunque la validacion avise.")
    sp.set_defaults(func=_cmd_inscribir)

    sp = sub.add_parser("anular", help="Anula una inscripcion (si no tiene nota).")
    sp.add_argument("cedula")
    sp.add_argument("--sede", required=True)
    sp.add_argument("--codigo", required=True)
    sp.add_argument("--periodo", required=True)
    sp.set_defaults(func=_cmd_anular)

    # --- Carga de notas / respaldos -------------------------------------- #
    sp = sub.add_parser("generar-carga",
                        help="Genera planilla .xlsx cifrada para un docente/UC.")
    sp.add_argument("--sede", required=True)
    sp.add_argument("--codigo", required=True)
    sp.add_argument("--turno", required=True)
    sp.add_argument("--seccion", required=True)
    sp.add_argument("--periodo", required=True)
    sp.add_argument("--password", default=None,
                    help="(Opcional) Contraseña a aplicar. Si se omite, se usa "
                         "la CLAVE MAESTRA de la sede, que el sistema conoce.")
    sp.add_argument("--destino", default=None)
    sp.set_defaults(func=_cmd_generar_carga)

    sp = sub.add_parser("importar-carga",
                        help="Importa una planilla llenada y graba las notas.")
    sp.add_argument("archivo")
    sp.add_argument("--sede", required=True)
    sp.add_argument("--password", default=None,
                    help="(Opcional) Contraseña que puso el docente. Si no se "
                         "indica, se intenta con la clave maestra.")
    sp.add_argument("--periodo", default=None)
    sp.add_argument("--previa", action="store_true",
                    help="Muestra las notas que se cargaran SIN escribir nada.")
    sp.set_defaults(func=_cmd_importar_carga)

    sp = sub.add_parser("respaldar",
                        help="Genera un .zip cifrado (AES) con los DBF de una sede.")
    sp.add_argument("--sede", required=True)
    sp.add_argument("--password", required=True)
    sp.add_argument("--destino", default=None)
    sp.set_defaults(func=_cmd_respaldar)

    sp = sub.add_parser("restaurar",
                        help="Restaura un respaldo cifrado dentro de las sedes.")
    sp.add_argument("zip")
    sp.add_argument("--password", required=True)
    sp.add_argument("--destino", default=None)
    sp.set_defaults(func=_cmd_restaurar)

    sp = sub.add_parser("estado", help="Resumen de una sede.")
    sp.add_argument("--sede", required=True)
    sp.set_defaults(func=_cmd_estado)

    sp = sub.add_parser("buscar", help="Datos de un estudiante por cedula.")
    sp.add_argument("cedula")
    sp.add_argument("--sede", required=True)
    sp.set_defaults(func=_cmd_buscar)

    sp = sub.add_parser("historial", help="Historial y promedio ponderado.")
    sp.add_argument("cedula")
    sp.add_argument("--sede", required=True)
    sp.set_defaults(func=_cmd_historial)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        return _gui()
    args = _parser().parse_args(argv)
    if not getattr(args, "func", None):
        _parser().print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
