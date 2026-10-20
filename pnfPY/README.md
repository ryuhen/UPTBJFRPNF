# pnfPY — Sistema Académico UPTJFR (Python, multi-sede)

Reimplementación en **Python** del sistema legado **"Sistema Juan"** (`pnf.exe`,
compilado con Harbour/xHarbour + HMG), con una diferencia clave respecto al
original: **trabaja varias sedes a la vez mediante carpetas**.

> El análisis de ingeniería inversa de `pnf.exe` (módulos, menús, reportes y
> modelo de datos) está en [`docs/ANALIS_pnf.md`](docs/ANALIS_pnf.md).

---

## 1. Idea central: carpetas por sede

El sistema legado asume **una sede por equipo** (`C:\SOCOPO\pnf.exe` +
`C:\SOCOPO\DATA\`). Aquí, en cambio, cada sede vive en su **propia carpeta**,
todas con la **misma estructura de archivos DBF**:

```
pnfPY\
├── pnf2.py # entrada (CLI + GUI)
├── gui.py                     # interfaz Tkinter (selector de sede + exportar)
├── core\
│   ├── dbf_reader.py          # lector DBF sin dependencias
│   ├── sedes.py               # descubrimiento de sedes y detección de entorno
│   ├── data_store.py          # carga e índice de una sede
│   ├── registro.py            # registro multi-sede (las 4 a la vez)
│   ├── historial.py           # historial + promedio ponderado
│   └── exportar.py            # copiar DBF a carpeta de sede y comprimir a .zip
├── datos\                     # carpeta de SEDES (modo multi-sede)
│   ├── barinas\DATA\
│   ├── barinitas\DATA\
│   ├── pedraza\DATA\
│   └── socopo\DATA\
├── datos_institucionales\     # cintillo, logos, bandera
└── docs\ANALIS_pnf.md
```

Cada `datos\<sede>\DATA\` es una copia/estructura idéntica de la `DATA` de esa
sede (`ALM.DBF`, `UFO.DBF`, `INS####.DBF`, `SEA####.DBF`, `CONFIG.DBF`, …).

---

## 2. Detección automática del entorno

Al arrancar, el programa mira cómo están organizados los datos:

| Modo | Cuándo | Comportamiento |
|---|---|---|
| **multi** | Existe una carpeta `sedes\` (o `datos\`) con subcarpetas por sede | Muestra un **selector de sede** y trabaja las cuatro (o más) a la vez |
| **simple** | Solo existe una carpeta `DATA\` junto al programa | Trabaja con esa DATA y **pide al coordinador que indique su sede** (se guarda en `sede.local.json`) |
| **vacio** | No hay `DATA` ni `sedes` | Avisa y pide colocar los datos |

Comando para ver el modo detectado:

```powershell
python pnf2.py entorno
```

---

## 3. Flujo del coordinador → director (exportar / instalar)

Un coordinador de sede trabaja en su equipo con su `DATA`. Para **enviar sus
datos al director**:

1. **Exportar** (botón en la GUI o CLI): copia los DBF de la sede a una carpeta
   con el **nombre de la sede** y la comprime en **`<sede>.zip`**.
2. El coordinador **envía el `.zip`** al director (correo/WhatsApp).
3. El director **coloca el ZIP** en su carpeta `sedes\` (o usa `instalar`) y ya
   puede trabajar esa sede **junto con las demás**.

```powershell
# Exportar una sede (o todas con --sede todas)
python pnf2.py exportar --sede socopo
#   -> exportaciones\socopo.zip

# Instalar un ZIP recibido dentro de la carpeta de sedes
python pnf2.py instalar .\exportaciones\socopo.zip --sedes .\datos
```

Estructura del paquete generado:

```
exportaciones\
├── socopo\           # copia de los DBF de la sede
│   └── DATA\
└── socopo.zip        # el paquete a enviar
```

---

## 4. Uso (CLI)

```powershell
python pnf2.py sedes                         # lista las sedes detectadas
python pnf2.py entorno                       # muestra el modo (multi/simple/vacio)
python pnf2.py estado --sede socopo          # resumen de una sede
python pnf2.py buscar 25079140 --sede socopo # datos de un estudiante
python pnf2.py historial 25079140 --sede socopo
python pnf2.py exportar --sede pedraza       # copia DBF y comprime a .zip
python pnf2.py instalar <zip> --sedes <dir>  # instala un .zip de sede

# --- Inscripcion --------------------------------------------------------
python pnf2.py oferta --sede socopo --periodo 2025 --trayecto 1
python pnf2.py inscritos 842_0030051 --sede socopo --periodo 2019
python pnf2.py inscripcion 25079140 --sede socopo --periodo 2020
python pnf2.py inscribir 25079140 --sede socopo --codigo 1205_0050162 --turno D --seccion A --periodo 2025
python pnf2.py anular 25079140 --sede socopo --codigo 1205_0050162 --periodo 2025
```

Sin argumentos abre la **GUI** (selector de sede + exportar).

---

## 4-bis. Carga de notas del docente (dos contraseñas)

Reproduce el flujo del sistema actual: el sistema **emite una planilla de carga**,
el docente **le pone su contraseña**, llena las notas y la devuelve.

### Las dos capas de contraseña

| Capa | Quién la conoce | Para qué |
|---|---|---|
| **1. Clave maestra** | El **sistema** (estable por sede, `datos/<sede>/clave_maestra.json`) | Garantiza que el sistema pueda reimportar la planilla **siempre**, sin pedir nada |
| **2. Clave del docente** | El **docente** (la ve y la escribe) | Es la que abre el `.xlsx`; es la que él usa |

> Un `.xlsx` solo admite **una** contraseña de apertura. Por eso el archivo se
> cifra con la clave **del docente** (como en el sistema actual) y el sistema
> guarda esa clave en el archivo lateral `.llave.json`. Al importar, el sistema
> la recupera sola: **nunca se la pide al coordinador ni al docente**.

### Comandos

```powershell
# 1) El coordinador genera la planilla para una seccion del docente
python pnf2.py generar-carga --sede socopo --codigo 976_0040513 \
    --turno N --seccion C --periodo 2008 --password "ClaveDocente2024"
#    -> carga_socopo_2008_976_0040513_NC.xlsx  (+ .llave.json)

# 2) El docente abre con SU contraseña, llena NOTA/ASISTENCIA y la devuelve

# 3) El coordinador ve primero las notas que se cargaran (no escribe nada)
python pnf2.py importar-carga archivo.xlsx --sede socopo --previa

# 4) Importacion definitiva (NO pide la contraseña del docente)
python pnf2.py importar-carga archivo.xlsx --sede socopo
```

Resultado de la importación: lista por cédula con **NOTA anterior / nueva /
asistencia / estado (OK, OMITIDA, error)** y "Notas importadas: N".

### Respaldos cifrados

```powershell
python pnf2.py respaldar --sede socopo            # genera respaldo_socopo_<fecha>.zip (AES)
python pnf2.py restaurar respaldo_socopo.zip --sede socopo
```

### Dependencias para esta parte

```powershell
pip install openpyxl msoffcrypto-tool pyzipper
```

---

## 5. Reglas académicas (ya validadas)

Tomadas de la bitácora del proyecto y confirmadas con los datos reales:

* **Nota mínima:** 12 general; **16 para el Proyecto** (`UFO.TIPO = 'P'`).
* **Promedio ponderado** = `Σ(nota × UC) / Σ(UC)`, por trayecto y total PNF.
* La constancia muestra la **última nota** por UC (la última aprobada si aprobó
  alguna vez).
* Se calculan **dos promedios**: con y sin el último año inscrito.

Prueba de referencia (Socopo, cédula 25079140): **total 194 créditos, promedio
de cursadas 15.22** — coincide con la bitácora.

---

## 5-bis. Carga de notas: dos capas de contraseña

El legado entrega un `.exe` al docente. Los correos y antivirus **bloquean los
ejecutables**, por eso pnfPY usa una **planilla `.xlsx` cifrada** (documento de
oficina: pasa sin problemas) con **dos capas de contraseña**:

| Capa | Quién la conoce | Para qué |
|---|---|---|
| **1. Clave maestra** | **Siempre el sistema** (`datos/<sede>/clave_maestra.json`) | Garantiza que pnfPY pueda **abrir e importar** la planilla sin pedir nada |
| **2. Clave del docente** | El docente (y el sistema la guarda en un lateral `.llave.json`) | Es la que el docente usa para abrir/editar su planilla |

Al generar la planilla se guarda junto a ella un `.llave.json` con la clave del
docente. Así, aunque el docente **vuelva a guardar el archivo cifrándolo con su
propia clave**, el sistema conoce esa clave y **puede abrirlo igual**.

### Flujo

```powershell
# 1) Generar la planilla (cifrada con la clave maestra)
python pnf2.py generar-carga --sede socopo --periodo 2019 \
    --codigo 1205_0050162 --turno D --seccion A
#    -> cargas_notas/carga_socopo_2019_1205_0050162_DA.xlsx
#       + .llave.json (clave del docente)

# 2) El docente abre, llena y devuelve la planilla.

# 3) VISTA PREVIA: ver las notas que se cargarán SIN escribir nada
python pnf2.py importar-carga cargas_notas/carga_....xlsx --sede socopo --previa

# 4) Cargar de verdad (no pide contraseña: usa la clave maestra)
python pnf2.py importar-carga cargas_notas/carga_....xlsx --sede socopo
```

La **vista previa** muestra `CEDULA | NOTA | ANTERIOR | ASISTENCIA | estado`, así
el coordinador revisa **qué se va a cargar antes de aceptarlo**, tal como en el
sistema actual.

### Respaldos cifrados

```powershell
python pnf2.py respaldar --sede socopo --password "clave-del-respaldo"
#   -> cargas_notas/respaldo_socopo.zip  (AES-256 real, con pyzipper)

python pnf2.py restaurar respaldo_socopo.zip --password "clave-del-respaldo"
```

Es un **ZIP de datos** (no un ejecutable), con **AES-256 real** (no el ZipCrypto
débil que dispara alertas), por lo que viaja por correo/redes sin bloqueos.

### Dependencias opcionales

```powershell
pip install openpyxl msoffcrypto-tool pyzipper
```

## 6. Estado

- [x] Núcleo multi-sede (detección, carga de las 4 sedes, índice por cédula).
- [x] Historial + promedio ponderado (validado contra la bitácora).
- [x] Detección de entorno (`sedes\` vs `DATA\`) y declaración de sede por el coordinador.
- [x] Exportar DBF a carpeta de sede + comprimir a `.zip` (e instalar el ZIP).
- [x] GUI Tkinter con selector de sede y botón de exportación.
- [x] **Módulo de INSCRIPCIÓN** (`core/inscripcion.py`):
  - [x] Oferta académica por periodo/trayecto (`SEA####`).
  - [x] Alumnos inscritos por Unidad Curricular (`INS####`).
  - [x] Inscribir / anular (escritura real en `INS####` + ajuste de `INSCRITOS` en `SEA####`).
  - [x] Validaciones del legado: duplicado, cédula registrada, cupo, trayecto.
  - [x] Protección de anulación si la UC ya tiene nota/asistencia.
- [x] **Carga de notas** (`core/carga_notas.py`):
  - [x] Planilla `.xlsx` cifrada (AES) con **dos capas de contraseña**.
  - [x] Clave maestra por sede (`clave_maestra.json`) → import automático.
  - [x] Clave del docente guardada en `.llave.json` → funciona si re-cifra.
  - [x] **Vista previa** (`--previa`) antes de escribir las notas.
  - [x] Respaldo/restauración en `.zip` con **AES-256** (pyzipper).
- [ ] Módulos restantes: **carga académica / asignación**, **reportes**
      y **actos de grado**.
- [ ] Constancias en PDF con membrete.
- [ ] Empaquetado portable con PyInstaller.

### Modelo de datos usado por la inscripción

| Tabla | Rol |
|---|---|
| `SEA####[IP].DBF` | **Oferta académica**: sección abierta (`UFO_CLAVE`, `TRAYECTO`, `TRAMO`, `TURNO`, `SECCION`, `CUPO`, `INSCRITOS`, `D_ID`, `ESTADO`) |
| `INS####[IP].DBF` | **Inscripciones** de cada estudiante (`A_ID`, `CODIGO`, `NOTA`, `ASISTENCIA`, `CONDICION`, `BORRAR`, `ESPECIAL`, `A_UNICA`) |
| `ALM.DBF` | Estudiantes (`A_ID`, `A_NOMBRE`, `A_APELLIDO`) |
| `UFO.DBF` | Catálogo de UC (`CODIGO`, `UFO_NOMBRE`, `UC`, `TIPO`, `TRAYECTO`) |
