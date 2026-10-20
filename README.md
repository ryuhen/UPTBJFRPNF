# UPTBJFRPNF — Sistema Juan / Socopo (reversa de `pnf.exe` + reimplementación Python)

🔗 **Repositorio:** https://github.com/ryuhen/UPTBJFRPNF

Repo **independiente** del proyecto `CASRCESUPABASE`. Aquí vive todo lo
relacionado con el sistema legado de Control de Estudios de la sede Socopo
(`pnf.exe`, Harbour/xBase, archivos DBF) y su reescritura en Python (`pnfPY`).

El repo original quedó en: `..\` (raíz `CASRCESUPABASE`, remoto
`github.com/ryuhen/CASRCESUPABASE.git`).

---

## Qué SÍ se versiona

| Ruta | Contenido |
|---|---|
| `pnfPY/` | Reimplementación en Python (`gui.py`, `pnf2.py`, `core/`). |
| `BITACORA_pnfNOTAS.md` | Bitácora de ingeniería inversa y decisiones. |
| `analiza_pcode.py` | Escáner de bloques de p-code Harbour dentro del EXE. |
| `reversa_pnf.py` | Extracción de cadenas / firmas del binario. |
| `ErrorLog.Htm`, imágenes, `CONFIG.DBF` de muestra | Recursos de referencia pequeños. |

## Qué NO se versiona (ver `.gitignore`)

- `otros proyectos/` → repos ajenos (`nvm`, `strix`, `DeepSeek-R1`, …).
- `rea/` → clon de `github.com/morluto/rea.git`.
- `DATA/`, `DATA - copia/`, `*.dbf`, `*.cdx` → bases del sistema original
  (**contienen datos personales**: cédulas, nombres, notas).
- `dataestudiantil2026/` → Excel/CSV/PDF con datos de estudiantes.
- `pnf.exe` y `pnf_strings.txt` → binario y volcado de strings (pesados;
  se pueden regenerar con `reversa_pnf.py`).

> Si algún día necesitas versionar el `.exe`, hazlo aparte con
> [Git LFS](https://git-lfs.com) (`git lfs track "*.exe"`), nunca en el
> historial normal.

---

## Uso rápido

```powershell
# Analizar los bloques de p-code del binario
python analiza_pcode.py pnf.exe

# Extraer cadenas del binario
python reversa_pnf.py pnf.exe

# Lanzar la reimplementación en Python
python pnfPY\gui.py
```

---

## Regenerar el repositorio

```powershell
git init
git add .
git commit -m "Inicio: reversa de pnf.exe (Harbour) y reimplementacion pnfPY"
git branch -M main
git remote add origin https://github.com/ryuhen/UPTBJFRPNF.git
git push -u origin main
```
