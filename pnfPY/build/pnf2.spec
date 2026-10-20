# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para pnfPY -> pnf2.exe

Genera un ejecutable UNICO (onefile) con GUI (Tkinter) y CLI, que incluye
las dependencias opcionales (openpyxl, msoffcrypto, pyzipper).

IMPORTANTE: el .exe NO incluye la carpeta `datos\\` (los DBF son datos del
coordinador, pueden pesar cientos de MB). El ejecutable lee `datos\\` y
`datos_institucionales\\` de la CARPETA DONDE ESTA EL .EXE (ver core/sedes.py
-> `_raiz_programa()`), igual que el pnf.exe legado.

Construir:
    pyinstaller build\\pnf2.spec --noconfirm
"""
import os

block_cipher = None

# La raiz del proyecto es la carpeta PADRE de esta carpeta `build`.
raiz = os.path.dirname(os.path.abspath(SPECPATH))
a = Analysis(
    [os.path.join(raiz, "pnf2.py")],
    pathex=[raiz],
    binaries=[],
    datas=[
        # Recursos institucionales (membrete/logo) -> se copian junto al exe.
        (os.path.join(raiz, "datos_institucionales"), "datos_institucionales"),
    ],
    hiddenimports=[
        "gui",
        "core",
        "core.dbf_reader",
        "core.sedes",
        "core.data_store",
        "core.registro",
        "core.historial",
        "core.exportar",
        "core.inscripcion",
        "core.carga_notas",
        "core.multiusuario",
        "openpyxl",
        "msoffcrypto",
        "pyzipper",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["numpy", "pandas", "matplotlib", "PIL"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="pnf2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,           # consola visible: la GUI sale con doble clic y el CLI funciona
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
