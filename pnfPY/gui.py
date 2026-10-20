# -*- coding: utf-8 -*-
r"""
pnfPY - Interfaz grafica (Tkinter, incluida en Python; sin dependencias).

Caracteristicas clave:
  * SELECTOR DE SEDE: si el programa detecta una carpeta `sedes\` (o `datos\`)
    con varias subcarpetas, muestra un combo para elegir la sede activa y
    trabaja las cuatro (o mas) sedes a la vez.
  * MODO UNA SOLA DATA: si solo hay una carpeta `DATA\`, trabaja con ella y
    pide al coordinador que indique a que sede pertenece (se guarda en
    `sede.local.json`).
  * BOTON EXPORTAR: copia los DBF de la sede activa a una carpeta con el
    nombre de la sede y la comprime en `<sede>.zip`, listo para enviar al
    director.

Ejecutar:
    python pnf2.py           (sin argumentos)
    python -m gui
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import Registro, resolver_entorno, guardar_sede_local
from core import exportar as EXP
from core import historial as H


AZUL = "#1a3a6b"
GRIS = "#f0f0f0"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("pnfPY - Sistema Academico UPTJFR (multi-sede)")
        self.geometry("980x640")
        self.minsize(860, 560)

        self.reg: Registro | None = None
        self.ds = None            # DataStore de la sede activa
        self.entorno = None

        self._construir_ui()
        self.after(100, self._detectar_entorno)

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #
    def _construir_ui(self) -> None:
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass

        # Barra superior: sede + estado
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Sede:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.var_sede = tk.StringVar()
        self.cmb_sede = ttk.Combobox(
            top, textvariable=self.var_sede, state="readonly", width=24,
        )
        self.cmb_sede.pack(side="left", padx=(6, 12))
        self.cmb_sede.bind("<<ComboboxSelected>>", self._on_cambiar_sede)

        self.btn_exportar = ttk.Button(
            top, text="Exportar DBF de la sede (.zip)", command=self._on_exportar,
        )
        self.btn_exportar.pack(side="left", padx=6)

        self.btn_recargar = ttk.Button(
            top, text="Recargar", command=self._detectar_entorno,
        )
        self.btn_recargar.pack(side="left", padx=6)

        self.lbl_estado = ttk.Label(top, text="Detectando...", foreground=AZUL)
        self.lbl_estado.pack(side="right")

        # Pestañas
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tab_info = ttk.Frame(self.nb, padding=8)
        self.tab_buscar = ttk.Frame(self.nb, padding=8)
        self.nb.add(self.tab_info, text="Informacion de la sede")
        self.nb.add(self.tab_buscar, text="Historial de estudiante")

        self._construir_tab_info()
        self._construir_tab_buscar()

        # Log inferior
        self.txt_log = tk.Text(self, height=6, bg=GRIS, state="disabled",
                               font=("Consolas", 9))
        self.txt_log.pack(fill="x", padx=8, pady=(0, 8))

    def _construir_tab_info(self) -> None:
        self.txt_info = tk.Text(self.tab_info, wrap="word",
                                font=("Consolas", 10))
        self.txt_info.pack(fill="both", expand=True)

    def _construir_tab_buscar(self) -> None:
        fila = ttk.Frame(self.tab_buscar)
        fila.pack(fill="x")
        ttk.Label(fila, text="Cedula:").pack(side="left")
        self.var_ced = tk.StringVar()
        ttk.Entry(fila, textvariable=self.var_ced, width=18).pack(side="left", padx=6)
        ttk.Button(fila, text="Buscar", command=self._on_buscar).pack(side="left")

        cols = ("codigo", "trayecto", "nota", "uc", "pond", "nombre")
        self.tree = ttk.Treeview(self.tab_buscar, columns=cols, show="headings")
        for c, t, w in (
            ("codigo", "Codigo", 130), ("trayecto", "T", 40),
            ("nota", "Nota", 60), ("uc", "UC", 60),
            ("pond", "Ponderado", 90), ("nombre", "Unidad Curricular", 420),
        ):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center" if c != "nombre" else "w")
        self.tree.pack(fill="both", expand=True, pady=(8, 0))

        self.txt_resumen = tk.Text(self.tab_buscar, height=6, bg=GRIS,
                                   font=("Consolas", 9))
        self.txt_resumen.pack(fill="x", pady=(6, 0))

    # ------------------------------------------------------------------ #
    #  Log
    # ------------------------------------------------------------------ #
    def log(self, msg: str) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    # ------------------------------------------------------------------ #
    #  Deteccion de entorno
    # ------------------------------------------------------------------ #
    def _detectar_entorno(self) -> None:
        self.entorno = resolver_entorno()
        self.reg = Registro()
        self.log(f"[entorno] modo={self.entorno.modo}: {self.entorno.mensaje}")

        if self.entorno.modo == "vacio":
            messagebox.showwarning(
                "Sin datos",
                "No se encontro ninguna carpeta DATA ni 'sedes'.\n\n"
                "Coloque la carpeta DATA junto al programa, o cree una carpeta "
                "'sedes' con una subcarpeta por sede (cada una con su DATA).",
            )
            self.lbl_estado.configure(text="Sin datos")
            return

        claves = self.reg.sedes_disponibles() or self.reg.sedes()
        self.cmb_sede.configure(values=claves)
        if claves:
            self.cmb_sede.set(claves[0])
            self._activar_sede(claves[0])

        if self.entorno.modo == "simple":
            # Pedir al coordinador que declare su sede.
            self._pedir_sede_coordinador()

    def _pedir_sede_coordinador(self) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Indique su sede")
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(
            dlg,
            text=("El programa esta usando una unica carpeta DATA.\n"
                  "Indique a que sede pertenece para etiquetar bien los datos:"),
            justify="left",
        ).pack(padx=16, pady=(16, 8), anchor="w")
        var = tk.StringVar(value=self.entorno.sedes[0].nombre if self.entorno.sedes else "")
        ent = ttk.Entry(dlg, textvariable=var, width=30)
        ent.pack(padx=16, pady=4, anchor="w")
        ent.focus_set()

        def aceptar():
            nombre = var.get().strip()
            if not nombre:
                return
            guardar_sede_local(nombre)
            self.log(f"[sede] declarada: {nombre} (sede.local.json)")
            dlg.destroy()
            self._detectar_entorno()

        ttk.Button(dlg, text="Guardar", command=aceptar).pack(padx=16, pady=12, anchor="e")

    def _on_cambiar_sede(self, _evt=None) -> None:
        self._activar_sede(self.var_sede.get())

    def _activar_sede(self, clave: str) -> None:
        if not clave:
            return
        self.lbl_estado.configure(text=f"Cargando {clave}...")
        self.update_idletasks()

        def trabajo():
            try:
                self.ds = self.reg.cambiar(clave)
                self.after(0, self._mostrar_info)
            except Exception as e:  # pragma: no cover
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=trabajo, daemon=True).start()

    def _mostrar_info(self) -> None:
        if self.ds is None:
            return
        r = self.ds.resumen()
        self.lbl_estado.configure(text=f"{r['sede']} lista")
        lineas = [
            f"SEDE: {r['sede']} ({r['clave']})",
            f"DATA        : {r['data_dir']}",
            "",
            f"Estudiantes : {r['estudiantes']}",
            f"Unidades UC : {r['unidades']}",
            f"PNF         : {r['pnf']}",
            f"Docentes    : {r['docentes']}",
            f"Periodos INS: {r['periodos']}",
            f"Inscripciones: {r['inscripciones']}",
            f"UC sin catalogo: {r['uc_sin_catalogo']}",
        ]
        if r.get("advertencias"):
            lineas.append("")
            lineas.append("Advertencias:")
            lineas += [f"  - {a}" for a in r["advertencias"]]
        self.txt_info.delete("1.0", "end")
        self.txt_info.insert("1.0", "\n".join(lineas))
        self.log(f"[sede] {r['sede']}: {r['estudiantes']} estudiantes, "
                 f"{r['inscripciones']} inscripciones")

    # ------------------------------------------------------------------ #
    #  Historial
    # ------------------------------------------------------------------ #
    def _on_buscar(self) -> None:
        if self.ds is None:
            messagebox.showinfo("Sede", "Primero seleccione/cargue una sede.")
            return
        ced = self.var_ced.get().strip()
        if not ced:
            return
        hist = H.construir_historial(self.ds, ced)
        self.tree.delete(*self.tree.get_children())
        if not hist.items:
            self.txt_resumen.delete("1.0", "end")
            self.txt_resumen.insert("1.0", f"Sin historial para {ced}.")
            return
        for it in hist.items:
            nota = "-" if it.nota is None else f"{it.nota:.0f}"
            self.tree.insert("", "end", values=(
                it.codigo, it.trayecto, nota, it.uc, f"{it.ponderado:.0f}", it.nombre,
            ))
        res = [f"Carrera: {hist.carrera}"]
        if hist.estudiante is not None:
            res.insert(0, f"{hist.estudiante.nombre_completo} (C.I. {hist.estudiante.cedula})")
        for tray in sorted(hist.por_trayecto):
            rr = hist.por_trayecto[tray]
            res.append(f"Trayecto {tray}: {rr.n_uc} UC, {rr.total_uc} creditos, "
                       f"promedio = {rr.promedio}")
        res.append(f"TOTAL: {hist.total.n_uc} UC, {hist.total_uc} creditos, "
                   f"promedio = {hist.total.promedio}")
        sin_ult = H.historial_sin_ultimo_anio(hist)
        if sin_ult is not hist.total:
            res.append(f"Sin ultimo anio ({hist.ultimo_anio}): promedio = {sin_ult.promedio}")
        self.txt_resumen.delete("1.0", "end")
        self.txt_resumen.insert("1.0", "\n".join(res))

    # ------------------------------------------------------------------ #
    #  Exportar
    # ------------------------------------------------------------------ #
    def _on_exportar(self) -> None:
        clave = self.var_sede.get()
        if not clave or self.reg is None:
            messagebox.showinfo("Exportar", "Seleccione una sede primero.")
            return
        sede = self.reg.sede(clave)
        if sede is None:
            return
        destino = filedialog.askdirectory(
            title="Carpeta donde guardar el paquete (.zip)",
        )
        if not destino:
            return
        self.lbl_estado.configure(text="Exportando...")
        self.update_idletasks()

        def trabajo():
            try:
                r = EXP.exportar_sede(sede, destino)
                self.after(0, lambda: self._exportado_ok(r))
            except Exception as e:  # pragma: no cover
                self.after(0, lambda: messagebox.showerror("Error al exportar", str(e)))

        threading.Thread(target=trabajo, daemon=True).start()

    def _exportado_ok(self, r: EXP.ResultadoExport) -> None:
        mb = r.tamano_bytes / (1024 * 1024)
        self.lbl_estado.configure(text="Exportado")
        self.log(f"[export] {r.sede}: {r.n_archivos} DBF -> {r.zip_path} ({mb:.1f} MB)")
        messagebox.showinfo(
            "Exportacion completada",
            f"Sede: {r.sede}\n"
            f"Archivos DBF: {r.n_archivos}\n"
            f"Paquete: {r.zip_path}\n"
            f"Tamano: {mb:.1f} MB\n"
            "Envie este .zip al director. El lo coloca en la carpeta 'sedes' "
            "de su equipo para trabajar la sede.",
        )


def main() -> int:
    App().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
