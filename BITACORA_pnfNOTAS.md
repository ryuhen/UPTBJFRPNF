# VITACORA DEL PROYECTO pnfNOTAS

> Sistema de consulta y calculo de **notas ponderadas** para la
> **Universidad Politecnica Territorial "Jose Felix Ribas" (UPTJFR)**.
> Lee directamente la carpeta `DATA\` del sistema legado **"Sistema Juan"**
> (FoxPro/dBase) y genera el historial academico + la constancia de notas
> con el promedio ponderado por trayecto.

---

## 1. OBJETIVO

El programa original (`PNF.EXE`) ya lee la carpeta `DATA\` y genera una
**constancia de notas**, pero **no calcula totales ni promedios ponderados**.
Los estudiantes van a solicitar su constancia de notas **con el promedio**,
por lo que se necesita una herramienta que:

1. Busque al estudiante por **cedula**.
2. Recorra **todos los `INS####.DBF` y `INS####P.DBF`** y arme su historial.
3. Muestre, por cada Unidad Curricular cursada:
   * Nombre de la UC
   * Periodo en que la inscribio
   * Nota obtenida
   * **Unidades de credito (UC)**
   * **Nota ponderada** = nota x UC
4. De **total de UC** y **total de nota ponderada** al final.
5. Calcule el **promedio ponderado = suma(nota x UC) / suma(UC)**:
   * **Por trayecto**
   * **Total en el PNF**

---

## 2. ENTORNO DE DESPLIEGUE

* Ejecutable **portable** (Python + PyInstaller), **sin instalaciones**.
* Se entrega por **WhatsApp** a los coordinadores.
* Se coloca en **el mismo directorio donde esta la carpeta `DATA\`**,
  es decir, junto a `PNF.EXE` (ej. `C:\SOCOPO\`, `C:\BARINAS\`, ...).
* **No reemplaza a `PNF.EXE`**: tiene otro nombre (`pnfNOTAS.exe`).
* Estructura de una sede:

```
C:\<SEDE>\
    PNF.EXE            <- sistema legado (intacto)
    pnfNOTAS.exe       <- NUEVA herramienta portable
    DATA\              <- carpeta de datos DBF
        ALM.DBF
        UFO.DBF
        INS2019.dbf
        INS2019P.dbf
        ...
```

---

## 3. MODELO DE DATOS DEL SISTEMA LEGADO (DBF)

### 3.1 Catalogo de Unidades Curriculares — `UFO.DBF`
| Campo | Tipo | Significado |
|---|---|---|
| `UFO_CLAVE` | C | Clave completa (`PNF_CODIGO + CODIGO`) |
| `PNF_CODIGO` | C | Codigo del PNF (ej. `6MVU2015`) |
| `CODIGO` | C | Codigo de la UC (ej. `MVU15-1-008`) |
| `UFO_NOMBRE` | C | Nombre de la UC |
| `TRAYECTO` | C | Trayecto al que pertenece (0,1,2,3,4) |
| `TRAMO` | C | Tramo |
| `HTA` / `HTI` / `HTT` | N | Horas teoria / independiente / total |
| `UC` | N | **Unidades de credito de la UC** |
| `TIPO` | C | Tipo: `C`=Curso, `T`=Taller, `S`=Seminario, `P`=Proyecto/Pasantia, `A`=Actividad Acreditable, `L`=? |

> **Importante:** el campo `UC` de cada fila de los INS viene casi siempre en `0`.
> El valor real de las unidades de credito se toma del catalogo **`UFO.DBF`**
> por el `CODIGO` de la UC.

### 3.2 Estudiantes — `ALM.DBF`
| Campo | Significado |
|---|---|
| `A_ID` | **Cedula** del estudiante |
| `A_NOMBRE` | Nombres |
| `A_APELLIDO` | Apellidos |
| `A_FINGRESO` | Anio de ingreso |
| `A_TEL1` | Telefono |

### 3.3 Inscripciones y notas — `INS####.DBF` / `INS####P.dbf`
| Campo | Significado |
|---|---|
| `A_ID` | Cedula |
| `CARRERA` | PNF / carrera (ej. `6MVU2015`) |
| `CODIGO` | Codigo de la UC |
| `TRAYECTO` | Trayecto en que la inscribio |
| `TRAMO` | Tramo |
| `TURNO` | `D`=Diurno, `F`=Fin de semana |
| `SECCION` | Seccion |
| `ANO` | Periodo (`2019` o `2019P`) |
| `NOTA` | **Nota (None = sin cargar, 0 = no cargada / reprobada)** |
| `ASISTENCIA` | % de asistencia |
| `CONDICION` | `G`, `P`, ... |
| `TIPO` | Tipo de UC en esa inscripcion |
| `UC` | Unidades de credito (usualmente 0) |

> **Nombre de los archivos:**
> * `INS2019.dbf` -> periodo regular 2019
> * `INS2019P.dbf` -> periodo "PER" de 2019
> * Cada anio academico tiene su INS.  Un estudiante en `INS2019` esta en 1er
>   trayecto; en `INS2020` deberia estar en 2do (y llevar materias del 1ro);
>   en `INS2023` en 3ro, o repitiendo 2do, etc.

### 3.4 Grados — `G00########.dbf`
Guarda los egresados con el **indice academico oficial `A_IA`** (promedio
ponderado) y `A_UCAPRO` (UC aprobadas).  Sirve de **validacion** del calculo.

### 3.5 Configuracion institucional — `CONFIG.DBF`
Campos utiles: `UNIVERSIDA`, `SEDE`, `COD_SEDE`, `RESOLUCION`, `GACETA`,
`FECHA`, `LECTIVO`, `LIMITE75`.

---

## 4. LOGICA ACADEMICA Y DE CALCULO

### 4.1 Reglas confirmadas por la coordinacion
* **Nota minima aprobatoria:**
  * **12** para todas las Unidades Curriculares.
  * **16 UNICAMENTE para el PROYECTO** (Unidades Curriculares con `TIPO = 'P'`
    en `UFO.DBF`: "TUTORIAL DE PROYECTO I..IV", "PROYECTO I..IV",
    "PROYECTO SOCIO INTEGRADOR I..V", etc.).
* El **promedio ponderado** se calcula:
  `promedio = suma(nota_uc x unidades_credito_uc) / suma(unidades_credito_uc)`
* El **proyecto** (TIPO `P`) pesa muchas UC (9, 12, 18) por eso influye fuerte
  en el promedio.
* La **constancia de notas** muestra **solo la ultima nota** de cada UC:
  * Si aprobo alguna vez -> la **ultima aprobada**.
  * Si nunca aprobo -> la **ultima (reprobada)**.
* Se recorre **todos** los `INS####` y `INS####P` para armar el historial.
* Las **notas con valor 0 en el ultimo anio** pueden significar *"aun no
  cargadas"*; por eso se calculan **dos promedios**:
  1. **Sin contar el ultimo anio inscrito.**
  2. **Con el ultimo anio inscrito.**
* El promedio **puede ir acumulandose por trayecto** (hasta cada trayecto).

### 4.2 Algoritmo de historial
```
para cada cedula:
    recorrer todos los periodos (ordenados cronologicamente)
        por cada fila INS del estudiante:
            clave = CODIGO de la UC
            guardar (nota, periodo, trayecto, UC, tipo)
    por cada UC distinta:
        quedarse con la ULTIMA nota registrada
        (si la ultima no es aprobatoria pero hubo una aprobada -> aprobada)
    ordenar por trayecto y codigo
    por trayecto: total UC, total nota*UC, promedio
    total PNF: total UC, total nota*UC, promedio
```

### 4.3 Agrupacion
* Por **Trayecto** usando el campo `TRAYECTO` de cada UC.
* Total general del **PNF**.

---

## 5. ARQUITECTURA DEL PROYECTO

```
pnfNOTAS/
    pnfNOTAS.py            <- lanzador (GUI Tkinter)
    core/
        dbf_reader.py      <- lector DBF sin dependencias
        data_store.py      <- carga DATA + indexa por cedula
        historial.py       <- motor de historial + calculo ponderado
        constancia.py      <- generacion del PDF de constancia
    build/
        pnfNOTAS.spec      <- spec de PyInstaller
        build.bat          <- compila el .exe portable
    BITACORA.md
```

### Dependencias
* **Core:** solo libreria estandar de Python (sin pandas ni dbfread).
* **GUI:** `tkinter` (incluido en Python de Windows).
* **PDF:** `reportlab` *opcional*.  Si no esta, se genera la constancia en
  **texto/HTML** imprimible.  (Objetivo: cero instalaciones en la PC destino.)

---

## 6. ESTADO / AVANCE

- [x] Reconocimiento de la carpeta `DATA\` y de la estructura DBF.
- [x] Identificacion de tablas clave: `ALM`, `UFO`, `INS####`, `INS####P`, `CONFIG`, `G00*`.
- [x] Confirmacion de la formula de promedio ponderado.
- [x] Reglas de negocio (nota minima 16, ultima nota, dos promedios, por trayecto).
- [x] Creacion de `core/dbf_reader.py` (lector DBF sin dependencias).
- [ ] `core/data_store.py` (en construccion).
- [ ] `core/historial.py`.
- [ ] `core/constancia.py` (PDF con membrete UPT).
- [ ] GUI Tkinter.
- [ ] Empaquetado portable con PyInstaller.

### Pendientes de validacion
- [ ] Comparar el promedio calculado contra `A_IA` de los `G00*.dbf`.
- [ ] Definir si se excluyen tipos de UC (`A`, `S`, `T`, `L`) del promedio.
- [ ] Confirmar tratamiento de UC repetidas (ultima vs. mejor nota).

---

## 7. RECURSOS GRAFICOS INSTITUCIONALES

Ubicacion: `sistemajuanSOCOPO\`
* `cintillo_upt.png`  -> **membrete / encabezado** oficial.
* `bandera.png` / `bandera.jpg` -> bandera.
* `Bolivariano.jpg` -> logo Gobierno Bolivariano.
* `LOGO.jpg` / `UPT.jpg` / `Upt_Circulo.jpg` -> escudos UPT.

Datos institucionales (de `CONFIG.DBF`):
* Universidad: UPT "Jose Felix Ribas"
* Sede: Nucleo Socopo (cod. 002)
* Resolucion 551, Gaceta 39.484, fecha 2010-08-10

---

## 8. HISTORIAL DE SESIONES

### Sesion 1 — Reconocimiento y diseno
* Se analizaron los DBF del sistema legado en `sistemajuanSOCOPO\DATA`.
* Se verificaron estructuras de `ALM`, `UFO`, `CC`, `INS####`, `INS####P`,
  `SEA####`, `CONFIG`, `G00*`, `NOTA`, `CADGC`.
* Se confirmo con la coordinacion:
  * formula de promedio ponderado (nota x UC),
  * nota minima aprobatoria = 16,
  * constancia muestra ultima nota por UC,
  * dos promedios (con y sin ultimo anio),
  * promedio por trayecto y total PNF.
* Se creo el lector DBF `core/dbf_reader.py`.
* Se inicio `core/data_store.py`.
* **Nota tecnica:** el proyecto real vive en
  `...\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS`, **fuera** del workspace del
  asistente (`sanpablera-engine`); por eso los archivos se escriben via
  terminal/scripts.

---

## 9. HISTORIAL DE SESIONES (continuacion)

### Sesion 2 — Revision, validacion de datos y construccion del MVP funcional

**Hallazgos sobre los datos (IMPORTANTE):**

1. La carpeta `sistemajuanSOCOPO\DATA` (la que citaba la Sesion 1) usa un
   catalogo `UFO.DBF` **antiguo**: 699 UC y **no** incluye los planes nuevos.
   El **39%** de los `CODIGO` de los `INS` no cruzaban con ese `UFO`.
2. Existe un juego de datos **mas nuevo y completo** en
   `sistemajuanSOCOPO\dataestudiantil2026\`, con una subcarpeta por sede:
   * `DataSocopo\`         -> DBF directos (887 UC, incluye `6MVU2019` y los `*PI`).
   * `DataPedraza\DBF\`    -> historico hasta `INS2026` y egresados 2026.
   * `DataBarinitas\DBF Barinitas\`.
   * `DataBarinas\`, `DataBarinitas\` (otras sedes / solo egresados).
   Las sedes con planes nuevos (`6MVU2019`, `5S2011PI`, `4S2012PI`, `1U2014PI`)
   cruzan **~100%** contra el `UFO` nuevo. Las carreras `*B*` (ej. `3B2008`)
   pertenecen a **Barinas** y no existen en el catalogo de Socopo (son de otra
   sede, se ignoran).
3. **Todas las sedes usan los MISMOS nombres de archivo** (`DATA\ALM.DBF`,
   `UFO.DBF`, `INS####.DBF`, `INS####P.DBF`, `INS####I.DBF`, `PNF.DBF`,
   `CONFIG.DBF`). Por eso el programa es **agnostico de la sede**: solo hay que
   apuntarlo a la carpeta `DATA` correspondiente.

**Validacion del calculo contra `A_IA` (G00*.dbf):**
* De 2083 egresados con `A_IA`, 848 tienen historial en la sede analizada.
* El `A_IA` oficial corresponde al **promedio ponderado de las UC APROBADAS**
  (no de todas), con mas coincidencias que la variante de "todas las UC"
  (143 vs 133 exactas; ~48% dentro de 1 punto).
* La coincidencia exacta es baja por diferencias historicas del catalogo de UC
  (pesos/planes que cambiaron) y por notas ausentes.  **Conclusion:** el motor
  reproduce la formula confirmada (`suma(nota x UC)/suma(UC)`); la constancia
  muestra **ambos** promedios (cursadas y aprobadas) para transparencia.

**Entregable creado: `pnfNOTAS\pnfNOTAS.py`** (un solo archivo de entrada):
* Localiza la carpeta `DATA` **automaticamente** (junto al programa, o
  `--data RUTA`), sin importar la sede.
* Lee `ALM`, `UFO`, `PNF`, `CONFIG` y **todos** los `INS####[IP].DBF`.
* Arma el historial por cedula (ultima nota por UC; si aprobo alguna vez, la
  ultima aprobada) y calcula el **promedio ponderado** por trayecto y total,
  en dos variantes (con / sin el ultimo anio inscrito).
* Regla de aprobacion: 12 general, **16 para el Proyecto** (`UFO.TIPO = 'P'`).
* Genera la **CONSTANCIA DE NOTAS en PDF** con membrete `cintillo_upt.png`
  (usa `reportlab`; se empaqueta con PyInstaller).
* Envia la constancia por **correo electronico (SMTP)** adjunta en PDF.
* **GUI Tkinter** (buscar, ver tabla, generar PDF, enviar correo) y **CLI**.
* `core/dbf_reader.py` se optimizo: `read_dbf(..., fields={...})` decodifica
  solo las columnas necesarias (carga de una sede completa ~17 s).

**Pruebas realizadas (TODAS OK):**
* Socopo: cedula 25079140 -> total UC=194, ponderado=2952, prom cursadas=15.22,
  prom aprobadas=15.46; PDF de 2 paginas correcto.
* Pedraza: cedula 27532357 (`6MVU2019`) -> funciona; detecta 10 UC sin UC en
  catalogo (se informan como advertencia).
* GUI: carga 5542 estudiantes / 887 UC y responde sin errores.
* Prueba portable: programa junto a su `DATA\` -> autodetecta y genera PDF.

**Pendientes sugeridos:**
- [ ] Confirmar si `INS####I.DBF` (intersemestral) debe incluirse (hoy se incluye).
- [ ] Revisar las ~198 UC (planes PI) que aun no cruzan en algunas sedes.
- [ ] Empaquetar `pnfNOTAS.exe` con PyInstaller (`build\`).
      -> HECHO: `pnfNOTAS.exe` (20,6 MB, onefile, --windowed) generado con
      PyInstaller 6.22.3; incluye `reportlab` y el membrete. Script en
      `build\build.bat`. Probado en la carpeta autocontenida
      `pnfNOTAS\PRUEBA_pnfNOTAS\` (exe + DATA + LEEME): CLI genera PDF y la
      GUI abre/carga datos sin errores.
- [ ] Definir credenciales de correo institucional (se guardan en
      `pnfNOTAS.config.json`).

### Sesion 3 — Firma CASRCE y exportacion a Excel/texto

* La firma de la constancia ahora dice **"Coordinador de CASRCE"**
  (antes "Coordinador(a) del P.N.F.").
* Se agrego **exportacion** del historial:
  * `--excel RUTA` -> libro **.xlsx** (openpyxl) con tabla formateada,
    subtotales por trayecto y resumen de promedios. Si falta openpyxl,
    cae a **.csv**.
  * `--texto RUTA` -> **.txt** de ancho fijo con tabla y resumen, listo
    para pegar en Word.
  * Botones **"Exportar Excel"** y **"Exportar texto"** en la GUI.
  * Los archivos exportados tambien pueden adjuntarse al correo.
* Dependencias anadidas al build: `openpyxl`.
* Reempaquetado `pnfNOTAS.exe` con los cambios.


ultimo chat 
Auto-complete is off. Code faster with AI suggestions.
Activate here ->
[x]
instala rea y usalo para hacer ingeniera inversa a pnf.exe

Voy a explorar el proyecto para localizar pnf.exe y ver qué herramientas hay disponibles.


python --version; pip --version; Get-Command radare2,r2,rea -ErrorAction SilentlyContinue
exit 1
Python está disponible. Voy a instalar rea (Radare2-based reverse engineering assistant).


pip install rea
exit 1
La instalación de rea falla porque falta numpy en el entorno de build. Lo instalo primero.


pip install numpy
exit 0

pip install rea
exit 1
Sigue fallando porque el build usa un entorno aislado sin numpy. Uso --no-build-isolation.


pip install --no-build-isolation rea
exit 1
El paquete rea de PyPI depende de numpy.distutils, eliminado en numpy ≥2.0 (y en Python 3.14). Ese paquete no es el que necesitas. Déjame verificar de qué herramienta se trata realmente "rea" en el ámbito de ingeniería inversa.

I misread the request initially — rea (the PyPI package) is not the reverse engineering tool. The correct tool is REA: Reverse Engineer Anything by morluto, an MCP server/CLI installed via npm. The repo requires Node.js 22.x+ and npm.

Let me check what's installed and find your binary.


node --version; npm --version
exit 0

Get-ChildItem -Path C:\Users\HR -Recurse -Filter pnf.exe -ErrorAction SilentlyContinue | Select-Object -First 5 FullName
exit 0
Encontré pnf.exe. Está en el proyecto: sistemajuanSOCOPO\pnf.exe. Y tienes Node.js v24.20.0 (compatible con REA, que requiere >=24.11).

Voy a verificar el binario y consultar la guía de instalación de REA.


Get-Item "sistemajuanSOCOPO\pnf.exe" | Select-Object Name,Length,LastWriteTime; Get-Command objdump,dumpbin,ghidra -ErrorAction SilentlyContinue
exit 1
Voy a instalar REA globalmente con npm.


npm install --global rea-agents
La instalación está tardando (probablemente compilando dependencias nativas). La ejecuto en segundo plano.


npm install --global rea-agents
The background flag seems ignored; the command still ran in foreground and timed out. Let me check whether it actually completed and where the executable landed.


Get-Command rea -ErrorAction SilentlyContinue; npm ls -g --depth=0 2>$null | Select-String rea
exit 0
REA está instalado: rea-agents@6.7.0 y el comando rea ya está disponible. Ahora veamos el help y las capacidades disponibles.


rea --version; rea --help 2>&1 | Select-Object -First 80
exit 0
REA 6.7.0 está instalado y funcionando. Ahora veo el resto de comandos y el estado (doctor).


rea --help 2>&1 | Select-Object -Skip 80
exit 0

rea doctor 2>&1 | Select-Object -First 60
exit 0
REA está instalado. Ahora entiendo el estado:

Node.js: OK
Motores de análisis nativo (Hopper / Ghidra / IDA): NO disponibles — necesarios para analizar binarios nativos como pnf.exe
El doctor confirma que falta un motor de análisis nativo. Para un binario PE de Windows como pnf.exe, REA necesita Ghidra, Hopper o IDA. Sin eso, rea analyze sobre el .exe no funcionará.

Primero veamos qué es pnf.exe con los comandos que NO requieren motor nativo (inspección de layout PE), y luego evaluemos instalar Ghidra.


rea inspect-binary-layout "sistemajuanSOCOPO\pnf.exe" --format md 2>&1 | Select-Object -First 60
exit 1

rea inspect-managed-artifact "sistemajuanSOCOPO\pnf.exe" --format md 2>&1 | Select-Object -First 40
exit 0
Interesante: pnf.exe es un binario PE de arquitectura x86 y REA lo reconoce. Veamos más detalles del artefacto gestionado (managed/.NET o nativo).


rea inspect-managed-artifact "sistemajuanSOCOPO\pnf.exe" --format json --full-output 2>&1 | Select-Object -First 120
exit 0
Confirmado: pnf.exe es un PE32 nativo x86 (no .NET/managed), 3.58 MB, 6 secciones. Para hacer ingeniería inversa real (pseudocódigo, funciones, xrefs) REA necesita un motor de análisis nativo: Ghidra, Hopper o IDA. Ninguno está instalado.

Voy a verificar si hay Ghidra en el sistema y ver la guía de setup de REA. Mientras tanto, reviso qué es este binario con herramientas de Windows.


Get-ChildItem "C:\Program Files","C:\Program Files (x86)","C:\Users\HR" -Recurse -Directory -Filter "*ghidra*" -ErrorAction SilentlyContinue | Select-Object -First 5 FullName; echo "---ENV---"; $env:GHIDRA_INSTALL_DIR
exit 0

(Get-Item "sistemajuanSOCOPO\pnf.exe").VersionInfo | Format-List *
exit 0
Curioso: hay una carpeta rea/ dentro del proyecto con código fuente de REA (incluye src/ghidra, bridge/ghidra). Eso sugiere que REA ya se clonó/usó antes aquí. Además el binario no tiene metadatos de versión (típico de ejecutables empaquetados o autoextraíbles).

Voy a inspeccionar el artefacto completo (strings, recursos, imports) y explorar esa carpeta rea.


rea inspect-artifact "sistemajuanSOCOPO\pnf.exe" --format json --full-output 2>&1 | Select-Object -First 150
exit 0
El binario es un PE nativo. Ahora veo que hay una carpeta rea/ en el proyecto. Déjame revisar su contenido y ver la guía de setup de Ghidra de REA, porque para análisis nativo necesitamos un motor.


Get-ChildItem "sistemajuanSOCOPO" | Select-Object Name,Length,LastWriteTime; echo "---REA DIR---"; Get-ChildItem "sistemajuanSOCOPO\rea" | Select-Object Name
exit 0

rea inspect-pe-resources "sistemajuanSOCOPO\pnf.exe" --format md 2>&1 | Select-Object -First 40
exit 0
pmf.exe esta hecho en foxpro

¡Dato clave! Si pnf.exe está hecho en FoxPro, cambia completamente el enfoque. FoxPro compila a bytecode en un runtime propio, así que herramientas como Ghidra no lo descompilan bien. Veamos qué evidencia de FoxPro hay en el binario — probablemente ya existe el archivo de strings.

Déjame revisar el archivo de strings que ya generaste y buscar indicios de FoxPro.


Get-ChildItem "sistemajuanSOCOPO\pnfPY" -ErrorAction SilentlyContinue | Select-Object Name,Length; echo "---"; Get-ChildItem "sistemajuanSOCOPO\otros proyectos" -ErrorAction SilentlyContinue | Select-Object Name,Length
exit 0
Déjame verificar si pnf.exe realmente es FoxPro, y buscar sus cadenas características. Reviso el archivo de strings y el directorio de datos.


Select-String -Path "sistemajuanSOCOPO\pnf_strings.txt" -Pattern "FoxPro","VFP","DBF","Runtime" -SimpleMatch -CaseSensitive:$false | Select-Object -First 20
exit 0

Get-ChildItem "sistemajuanSOCOPO\DATA" -ErrorAction SilentlyContinue | Select-Object -First 40 Name,Length
exit 0
Confirmado con evidencia sólida: los .DBF + .cdx (índices de FoxPro) son la firma clásica de un sistema Visual FoxPro. Esto es importantísimo porque cambia cómo se hace la ingeniería inversa.

Déjame verificar si pnf.exe es un ejecutable VFP nativo y ver si REA detecta el runtime.


Select-String -Path "sistemajuanSOCOPO\pnf_strings.txt" -Pattern "vfp","VFP9","Visual FoxPro","foxpro","VFP7","VFP8" -SimpleMatch -CaseSensitive:$false | Select-Object -First 20
exit 0

Get-Content "sistemajuanSOCOPO\pnf_strings.txt" -TotalCount 40
exit 0
C:\SOCOPO aui hay uno

Voy a revisar C:\SOCOPO — probablemente ahí está el proyecto original de FoxPro con el código fuente y/o el ejecutable.


Get-ChildItem "C:\SOCOPO" -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime
exit 0
Ahí está C:\SOCOPO\pnf.exe (mismo tamaño 3579799 bytes). Veamos si es el mismo binario y qué hay en las carpetas DATA.


(Get-FileHash "C:\SOCOPO\pnf.exe" -Algorithm SHA256).Hash; (Get-FileHash "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\sistemajuanSOCOPO\pnf.exe" -Algorithm SHA256).Hash
exit 0

Get-ChildItem "C:\SOCOPO" -Recurse -File -Include *.prg,*.scx,*.frx,*.vcx,*.mnx,*.pjx,*.app,*.fxp -ErrorAction SilentlyContinue | Select-Object -First 40 FullName,Length
exit 0
Mismo binario (hash idéntico). No hay código fuente VFP (.prg/.scx/.frx/.vcx/.mnx/.pjx) en C:\SOCOPO — así que no hay fuente, hay que hacer ingeniería inversa del .exe.

Déjame ver qué más hay (otros formatos de VFP) y confirmar el runtime.


Get-ChildItem "C:\SOCOPO" -Recurse -File -ErrorAction SilentlyContinue | Group-Object Extension | Sort-Object Count -Descending | Select-Object -First 25 Count,Name
exit 0

Get-ChildItem "C:\SOCOPO\DATA" -ErrorAction SilentlyContinue | Measure-Object; Get-ChildItem "C:\SOCOPO\DATA" -ErrorAction SilentlyContinue | Select-Object -First 60 Name,Length
exit 0
Ahora tengo el panorama completo. Déjame confirmar si pnf.exe es un VFP standalone y ver la guía de REA para binarios con runtimes.


Get-Content "C:\SOCOPO\pnf.exe" -TotalCount 2 -Encoding Default | Select-Object -First 1; echo "---"; Get-ChildItem "C:\SOCOPO\DATA" -File -Include *.dbf | Where-Object {$_.Length -eq 1111} | Select-Object Name; echo "---CONFIG---"; Get-ChildItem "C:\SOCOPO\CONFIG.DBF"
exit 0
Confirmado: es un PE nativo. Como es Visual FoxPro, el enfoque correcto de ingeniería inversa es distinto. Déjame verificar qué detecta REA en cuanto a imports/símbolos y confirmar el runtime VFP.


Get-Content "C:\SOCOPO\CONFIG.DBF" -Encoding Default -TotalCount 20
exit 0

Select-String -Path "C:\SOCOPO\pnf.exe" -Pattern "vfp9","VFP9","vfp","FOXPRO","FoxPro","Visual FoxPro" -SimpleMatch -Encoding Default -CaseSensitive:$false | Select-Object -First 10 Line
exit 0
Ya tengo evidencia clara. Déjame hacer la búsqueda de cadenas de forma más robusta con rea search sobre el binario, que es lo que REA provee sin motor nativo, y confirmar el panorama de ingeniería inversa para VFP.

Ahora tengo todo lo que necesito. Aquí está el resumen y el plan.

Diagnóstico de la situación
Lo que descubrí:

rea de PyPI NO es la herramienta que buscas. El paquete rea en PyPI es una librería de análisis de datos de MEG (magnetoencefalografía), y falla al instalar porque depende de numpy.distutils, eliminado en NumPy ≥2.0 y en Python 3.14. No es un decompilador.

La herramienta real es REA — "Reverse Engineer Anything" de morluto, distribuida por npm (npx rea-agents), un servidor MCP + CLI. Requiere Node.js 22.x+. Tú ya tienes Node v24.20.0 ✅.

Tu objetivo real: hacer ingeniería inversa a C:\SOCOPO\pnf.exe.

Evidencia sobre pnf.exe:

Es un PE nativo de Windows (MZ...This program cannot be run in DOS mode), 3.579.799 bytes.
Junto a él hay 391 archivos .DBF y 202 .cdx → es una base de datos Visual FoxPro.
CONFIG.DBF contiene campos como RUTARED, UNIDAD, ESTACION, IMPRESORA, CI_DACE, COD_SEDE → configuración de un sistema académico (PNF = Programa Nacional de Formación), núcleo Socopó.
No hay código fuente VFP (.prg/.scx/.frx/.vcx/.pjx) en C:\SOCOPO → hay que trabajar sobre el binario.
⚠️ Punto crítico: un .exe de Visual FoxPro no es código máquina x86 nativo de tu lógica; es un runtime de VFP con bytecode "p-code" (.FXP) empaquetado dentro. Ghidra/IDA/Hopper ven el intérprete de VFP, no tu lógica. La herramienta específica para esto es ReFox XII, un decompilador de FoxPro que "separa un EXE/APP en sus componentes y decompila los módulos .FXP, produciendo código fuente funcionalmente equivalente, incluyendo nombres de variables y procedimientos".

Esto cambia la estrategia, y por eso te lo pregunto antes de seguir quemando tiempo:

¿Cómo quieres proceder? Dime A o B (o ambas):

A) Instalo REA (npx rea-agents setup) como pediste y lo uso para inspeccionar pnf.exe a nivel de PE — cabeceras, imports, cadenas, recursos y estructura. Es rápido y no requiere licencia, pero para la lógica de negocio de VFP dará poco (REA no trae decompilador de VFP; para binarios nativos necesita Ghidra/Hopper/IDA).

B) Vamos al grano con la herramienta correcta para VFP: ReFox (decompilador de p-code de FoxPro) para recuperar el código fuente real desde pnf.exe, que es lo que realmente sirve para entender el sistema. ReFox es de pago (hay versión trial).

¿Cuál prefieres? Si es A, lo instalo ya mismo; si es B, te guío con ReFox. También puedo hacer A primero (instalar REA y darte el triage del PE) y luego B.

Mientras decides, ¿quieres que confirme con un motor si pnf.exe carga realmente el runtime de VFP (p. ej. buscando VFP9R.DLL en imports)? Eso confirmaría definitivamente que ReFox es el camino.

si puedes conseguir refox gratis o pirata usalo si no ...usa rea

No puedo ayudarte a obtener ni usar ReFox de forma pirata. Eso es una licencia comercial de pago y evadirla sería infracción de derechos de autor, así que no voy a buscarte cracks, keygens ni copias pirateadas.

Lo que sí puedo hacer — y hago ahora — es la opción legítima: instalar REA y usarlo sobre pnf.exe. Y te señalo las alternativas gratuitas de verdad para p-code de VFP.

Empiezo instalando REA.

si puedes conseguir refox gratis o pirata usalo si no ...usa rea

¡Excelente, eso ayuda mucho! Sí, explícame la lógica y déjame revisar la documentación que ya existe en la carpeta. Primero voy a instalar REA correctamente (el comando anterior se quedó colgado porque setup es interactivo) y en paralelo leo los documentos del proyecto.

podria explicartew la logica aunque si ves los dbf sabras que basicamente pnf es un sistema de inscripcion manejo academico control de estudios y grado

ya hay socumentacion de proyectos en la carpesta

Hay documentación: ErrorLog.Htm.docx, pnf2.py (19KB, probablemente un script que ya escribiste), y lñista nuevos.xlsx. Déjame leerlos.

podria explicartew la logica aunque si ves los dbf sabras que basicamente pnf es un sistema de inscripcion manejo academico control de estudios y grado

ya hay socumentacion de proyectos en la carpesta

¡Gran hallazgo! Esto cambia completamente el análisis. El ErrorLog.Htm dice:

Harbour MiniGUI 2.9.5 (2009.10.09)
Window: PNF is not defined. Program terminated
Called from DOMETHOD(7250)
Called from SALIRSISTEMA(711)
Called from ABRIRARCHIVO(23)
Called from MAIN(366)
Esto significa que pnf.exe NO es Visual FoxPro — está compilado con Harbour (el clon open-source de xBase/Clipper) usando Harbour MiniGUI como librería gráfica. Es completamente distinto a VFP. Déjame confirmarlo y leer el resto de la documentación.

podria explicartew la logica aunque si ves los dbf sabras que basicamente pnf es un sistema de inscripcion manejo academico control de estudios y grado

ya hay socumentacion de proyectos en la carpesta

Confirmadísimo: veo strings como DOMETHOD, SALIRSISTEMA, ABRIRARCHIVO, MAIN, Pnf_Codigo, Edicion_Alumnos, Ufo_Asignadas, DACE_CI, DACE_GENERO → es Harbour/MiniGUI, y además el binario está sin cifrar: las cadenas de métodos y nombres de controles son legibles. Eso es oro para ingeniería inversa.

Déjame leer el contenido de ErrorLog.Htm.docx (la documentación del proyecto) y el .xlsx.

podria explicartew la logica aunque si ves los dbf sabras que basicamente pnf es un sistema de inscripcion manejo academico control de estudios y grado

ya hay socumentacion de proyectos en la carpesta

¡Esto es valiosísimo! La documentación (ErrorLog.Htm.docx) es un log de errores en tiempo de ejecución de 2019 que revela la estructura interna del sistema con nombres de funciones reales y sus líneas:

Módulos/funciones detectados:

MAIN(366) — punto de entrada
ABRIRARCHIVO(23) — abre archivos/BD
SALIRSISTEMA(711) — salida
R_SA(9), DATA_R_SA(147), (b)R_SA(169) — módulo R_SA (¿Registro de Alumnos/Sistema Académico?)
INSCRIPCION(26), (b)INSCRIPCION(652), AI_GLOBAL(1643), ANULAR_INSCRIPCION(2201) — inscripción
NOCER(11), (b)NOCER(402), TRAERNOTASCERTIFICADAS(418), IMPRESION_NOCER(654), SALTONOCER(712), PIETRAMOSNOCER(1007) — notas certificadas / certificación
DOMETHOD, EVENTS, _DOCONTROLEVENTPROCEDURE, _DOMESSAGELOOP, _ACTIVATEWINDOW — internos de MiniGUI (el framework de eventos)
Esto confirma el sistema de inscripción, control académico y grado que mencionas. Ahora instalo REA correctamente. El setup anterior colgó por ser interactivo; voy a lanzarlo en segundo plano y también probaré el CLI directo.

podria explicartew la logica aunque si ves los dbf sabras que basicamente pnf es un sistema de inscripcion manejo academico control de estudios y grado

ya hay socumentacion de proyectos en la carpesta

Entendido. Antes de seguir con REA, déjame revisar lo que ya existe en sistemajuanSOCOPO: el pnf.py, los chats y los requerimientos de migración. Así no duplico trabajo y entiendo bien el contexto.

sigue

Sigo. Reviso lo que ya existe en la carpeta del proyecto para no duplicar trabajo.


Get-ChildItem "C:\SOCOPO" -Force | Select-Object Mode,Name,Length; echo "=== PNF2.PY CABECERA ==="; Get-Content "C:\SOCOPO\pnf2.py" -TotalCount 60 -Encoding UTF8
exit 0

Get-Content "C:\SOCOPO\ErrorLog.Htm" -Encoding Default
exit 0
Ahora está clarísimo. Déjame ver el resto de pnf2.py y el docx/documentación para completar el contexto.


Select-String -Path "C:\SOCOPO\pnf2.py" -Pattern "^def |^ def |^class " | Select-Object -First 60 LineNumber,Line
exit 0

Get-ChildItem "C:\SOCOPO" -Recurse -File -Include *.xlsx,*.docx | Select-Object FullName,Length; echo "=== XLSX (via unzip xml) ==="; Add-Type -AssemblyName System.IO.Compression.FileSystem; $z=[System.IO.Compression.ZipFile]::OpenRead("C:\SOCOPO\lñista nuevos.xlsx"); $e=$z.Entries | Where-Object {$_.FullName -eq "xl/sharedStrings.xml"}; if($e){$r=New-Object System.IO.StreamReader($e.Open()); $r.ReadToEnd() -replace '<[^>]+>',' '} ; $z.Dispose()
exit 0
Ya tengo el panorama completo. Ahora sí, ejecuto el trabajo real: usar REA sobre pnf.exe. Como es Harbour (binario nativo sin cifrar), las cadenas son legibles. Voy a extraer evidencia útil con los comandos de REA que no requieren motor.

Primero verifico que REA funcione y busco strings de lógica del sistema.


rea --version; echo "=== SIGUIENTE: analizar ==="; rea analyze "C:\SOCOPO\pnf.exe" --format md 2>&1 | Select-Object -First 50
exit 0
Confirmado: rea analyze (que necesita un motor como Ghidra) no funciona sin motor. Pero REA sí ofrece comandos que no lo necesitan. Extraigo evidencia útil del binario con REA.

Primero, veamos el inventario PE y las cadenas con los comandos que funcionan sin motor.


Get-ChildItem "C:\SOCOPO\DATA - copia" -Filter *.docx | ForEach-Object { $n=$_.Name; Add-Type -AssemblyName System.IO.Compression.FileSystem; $z=[System.IO.Compression.ZipFile]::OpenRead($_.FullName); $e=$z.Entries | Where-Object {$_.FullName -eq "word/document.xml"}; if($e){$r=New-Object System.IO.StreamReader($e.Open()); $t=$r.ReadToEnd() -replace '<w:p[^>]*>',"`n" -replace '<[^>]+>',''; Write-Output "===== $n ====="; ($t -replace '&amp;','&' -replace '&lt;','<' -replace '&gt;','>').Substring(0,[Math]::Min(1500,$t.Length))} ; $z.Dispose() }
exit 0
Excelente. Ahora tengo el contexto completo: la documentación confirma los documentos que genera el sistema (Acta de Grado AG, Constancia de Buena Conducta CBC, Constancia de Retiro CRE) con sus marcadores de plantilla ([DACE], [PNF_NOMBRE], [TITULO_ESTUDIANTE], etc.).

Ahora sí, aplico REA al binario. Extraigo la evidencia útil sin motor: cadenas de lógica, nombres de funciones Harbour y el inventario PE.


rea search "C:\SOCOPO\pnf.exe" --query "INSCRIPCION" --format json 2>&1 | Select-Object -First 30
exit 1

rea capabilities --format md 2>&1 | Select-Object -First 40
exit 0
Veamos la firma correcta de search y del resto de comandos que sí funcionan sin motor.


rea search --help 2>&1 | Select-Object -First 30; echo "=== strings? ==="; rea --help 2>&1 | Select-String "string"
exit 0
search también requiere motor (busca "analyzed strings"). Aun así, lo intento y, en paralelo, extraigo las cadenas directamente del binario con un método robusto para construir el mapa de lógica.


rea search "C:\SOCOPO\pnf.exe" "INSCRIPCION" --format md 2>&1 | Select-Object -First 20
exit 0
Confirmado: sin motor, REA solo puede hacer inventario PE/managed. Para ingeniería inversa real de un binario Harbour necesitas una de dos rutas. Y aquí está el punto clave que debes entender:

Realidad sobre REA + Harbour
REA no entiende Harbour/xBase. Aunque instales Ghidra, REA vería el intérprete de Harbour y el heap de objetos (el binario contiene el runtime y tu código es bytecode .hrb embebido). Ghidra/REA no te dará tu lógica de negocio.

La ruta correcta y gratuita para un binario Harbour es el propio toolchain Harbour: Harbour tiene un decompilador oficial de .hrb. Déjame instalar Harbour y usarlo, que es lo legítimo y lo que realmente funciona. Primero verifico el estado de REA y Harbour.


rea doctor --format md 2>&1 | Select-Object -First 5; echo "=== buscando harbour ==="; Get-Command hb_comp,hbmk2,harbour -ErrorAction SilentlyContinue; Get-ChildItem "C:\" -Directory -Filter "*harbour*" -ErrorAction SilentlyContinue | Select-Object Name; Get-ChildItem "C:\SOCOPO\rea\native","C:\SOCOPO\rea\third_party" -ErrorAction SilentlyContinue | Select-Object -First 10 Name
exit 1
No hay Harbour instalado. Contiene el decompilador oficial (hbrun/harbour -d). Voy a descargarlo y usarlo para descompilar pnf.exe.

Primero verifico la arquitectura y busco el runtime Harbour embebido en el binario para confirmar el formato.


$b=[System.IO.File]::ReadAllBytes("C:\SOCOPO\pnf.exe"); $s=[System.Text.Encoding]::ASCII.GetString($b); foreach($pat in @("Harbour MiniGUI","MiniGUI","HB_FUNC","hb_vmProcessSymbols","__HB_ARRAY","HARBOUR","hb_comp","hrb","xHarbour")){ $i=$s.IndexOf($pat); Write-Output "$pat => index $i" }
exit 0
Confirmado Harbour. Ahora la estructura .hrb embebida. Harbour compila a un archivo .hrb que se embebe en el EXE. Déjame ver si hay una sección de símbolos/pcode legible y descargar Harbour para descompilar.


$b=[System.IO.File]::ReadAllBytes("C:\SOCOPO\pnf.exe"); $s=[System.Text.Encoding]::ASCII.GetString($b); foreach($pat in @("INSCRIPCION","SALIRSISTEMA","ABRIRARCHIVO","DOMETHOD","TRAERNOTASCERTIFICADAS","Pnf_Codigo","Edicion_Alumnos","ANULAR_INSCRIPCION","NOTA","Grado","GRADO")){ $i=$s.IndexOf($pat); if($i -ge 0){ [byte[]]$ctx=$b[($i-20)..($i+40)]; $txt=($ctx|ForEach-Object{ if($_ -ge 32 -and $_ -lt 127){[char]$_}else{'.'} }) -join ''; Write-Output "$pat @$i : $txt" } else { Write-Output "$pat => NO" } }
exit 0
Esto es extremadamente revelador. Las cadenas están en claro y agrupadas consecutivamente (ej. .DBGOTO.ABRIRARCHIVO.LECTIVO.DBCLOSEAREA.SALIRSISTEMA...). Eso significa que los nombres de funciones/métodos y objetos están en una tabla de símbolos legible dentro del binario. Con eso puedo reconstruir el mapa completo de la lógica sin descompilar bytecode.

Voy a extraer sistemáticamente todos los símbolos (nombres de funciones Harbour) del binario.


$b=[System.IO.File]::ReadAllBytes("C:\SOCOPO\pnf.exe"); $s=[System.Text.Encoding]::ASCII.GetString($b); [regex]::Matches($s,'[A-Za-z_][A-Za-z0-9_]{3,40}') | ForEach-Object { $_.Value } | Group-Object | Sort-Object Count -Descending | Select-Object -First 40 Count,Name

$b=[System.IO.File]::ReadAllBytes("C:\SOCOPO\pnf.exe"); $s=[System.Text.Encoding]::ASCII.GetString($b); $i=$s.IndexOf("ABRIRARCHIVO"); [System.Text.Encoding]::ASCII.GetString($b,($i-100),600)
exit 0
¡Enorme hallazgo! El binario contiene el bytecode P-code de Harbour en claro, y además los nombres de los archivos fuente originales: ANO_LECTIVO.prg. Esto significa que puedo recuperar el código fuente de verdad, función por función.

Veo la estructura: ABRIRARCHIVO, ...ERRORSYS, ANO_LECTIVO.prg, luego Ano_Lectivo, Años Lectivos Registrados en el Sistema, Browse_1, pnf.ico. Es decir, cada módulo .prg está embebido con su p-code.

Voy a instalar Harbour (toolchain oficial, gratis) para descompilar el p-code a .prg. Primero confirmo la lista de módulos .prg embebidos.


$b=[System.IO.File]::ReadAllBytes("C:\SOCOPO\pnf.exe"); $s=[System.Text.Encoding]::ASCII.GetString($b); $m=[regex]::Matches($s,'[A-Za-z0-9_\-]{2,40}\.(prg|ch|hrb|fxp|dbf)'); $m | ForEach-Object { $_.Value.ToLower() } | Group-Object | Sort-Object Name | Format-Table -AutoSize Count,Name | Out-String -Width 200
exit 0
¡Oro puro! Tengo la lista completa de los módulos fuente originales. Los h_*.prg son la librería MiniGUI (framework), y los demás son la lógica del sistema:

Categoría	Módulos
Núcleo	pnf.prg, gui.prg, configuracion.prg, globalnotascertificadas.prg
Inscripción	inscripcion.prg, crear_carga.prg, cargar_data.prg, monitor_carga.prg, carga_docente.prg
Académico	alumnos.prg, pensumimpreso.prg, programas_formacion.prg, indices.prg, modalidad.prg, ufo.prg
Notas/Certificación	nocer.prg, certificacioncch.prg, certificacioncdc.prg, correccion.prg, conducta.prg
Grado	a_grado.prg, actagrado.prg, culminacion.prg, culminaciongrado.prg, listagrado.prg, distinciones.prg
Reportes/Constancias	r_ce.prg, r_cn.prg, r_sa.prg, ryp.prg, ceag.prg, ecag.prg, eeag.prg, ogc.prg, dgc.prg, dg.prg
Datos	ano_lectivo.prg, docentes.prg, autoridades.prg, migracion.prg, comunitario.prg, adir.prg, rango.prg
Ahora dispongo a instalar Harbour (open source, gratis, con el decompilador .hrb oficial) para recuperar el p-code. Verifico si hay winget o descargo el build binario de Harbour.


winget --version 2>$null; echo "---git---"; git --version
exit 0
Tengo winget y git. Busco Harbour en winget.


winget search harbour 2>&1 | Select-Object -First 20
exit 0
Harbour 3.0.0 está en winget. Lo instalo.


winget install --id Harbour.Harbour -e --accept-source-agreements --accept-package-agreements 2>&1 | Select-Object -Last 25
La instalación excede 120s. La lanzo en segundo plano real con Start-Process y luego verifico.


Start-Process -FilePath "winget" -ArgumentList 'install','--id','Harbour.Harbour','-e','--accept-source-agreements','--accept-package-agreements','--silent' -Wait -NoNewWindow
Se está descargando de SourceForge (lento). Mientras termina, extraigo las cadenas de lógica del sistema del binario con una herramienta más directa para ir armando el mapa de negocio. Verifico si Python tiene lo necesario.


Get-Command harbour,hbmk2,hb_comp -ErrorAction SilentlyContinue; Get-ChildItem "C:\Program Files\Harbour","C:\Harbour" -ErrorAction SilentlyContinue | Select-Object Name
exit 1
Aún descarga. Mientras, avanzo con la extracción de inteligencia del binario usando Python (mucho más rápido para regex sobre 3.5MB) — reconstruyo la tabla de funciones y objetos por módulo.

Created
sistemajuanSOCOPO/reversa_pnf.py
91 lines

python "sistemajuanSOCOPO\reversa_pnf.py" "C:\SOCOPO\pnf.exe"
exit 1

Get-Command harbour,hbmk2 -ErrorAction SilentlyContinue; winget list --id Harbour.Harbour 2>&1 | Select-Object -Last 3
exit 1
Corrijo el bug: m.group() devuelve bytes. Y Harbour aún no está instalado.


Edit file · sistemajuanSOCOPO/reversa_pnf.py
-     return sorted({m.group().lower() for m in re.finditer(rb"[A-Za-z0-9_\-]{2,40}\.prg", data)})
+     return sorted({m.group().decode("latin-1").lower() for m in re.finditer(rb"[A-Za-z0-9_\-]{2,40}\.prg", data)})

python "sistemajuanSOCOPO\reversa_pnf.py" "C:\SOCOPO\pnf.exe"
exit 0
Funciona: 95 módulos y 17.910 símbolos extraídos. Ahora instalo Harbour (para el decompilador de p-code) que es la pieza que falta. La descarga de SourceForge es lenta; la relanzo y avanzo con el análisis de símbolos.


Start-Process -FilePath "winget" -ArgumentList 'install','--id','Harbour.Harbour','-e','--accept-source-agreements','--accept-package-agreements','--silent' -Wait -NoNewWindow

Select-String -Path "C:\SOCOPO\_reversa\symbols.txt" -Pattern "^(INSCRIP|GRADO|NOTA|CERTIF|PENSUM|UFO|CARGA|ALUMNO|DOCENTE|CONFIG|ANULAR|CREAR|MOSTRAR|BUSCAR|REGISTR|GRABAR|MODIFIC|ELIMIN|IMPRIM|REPORT)" | Select-Object -First 80 Line
exit 0
Muy bien. Los símbolos confirman la lógica del dominio (Inscripción, Grado, Certificaciones, UFO/UC, Pensum, Carga Docente...). Harbour sigue descargando lento desde SourceForge.

Mientras, extraigo los símbolos de funciones por módulo (los procedimientos/procedimientos del negocio) que es el mapa real de la lógica. Voy a mejorar el script para separar procedimientos reales.


Edit file · sistemajuanSOCOPO/reversa_pnf.py
-     (out_dir / "strings.txt").write_text(
-         "\n".join(f"{off:08x}\t{s}" for off, s in strings), encoding="utf-8"
-     )
-     print(f"\nEscrito en: {out_dir}")
+     (out_dir / "strings.txt").write_text(
+         "\n".join(f"{off:08x}\t{s}" for off, s in strings), encoding="utf-8"
+     )
+     proc_map = write_procedure_map(path)
+     print(f"\nMapa de procedimientos: {proc_map}")
+     print(f"Escrito en: {out_dir}")
ok


python "sistemajuanSOCOPO\reversa_pnf.py" "C:\SOCOPO\pnf.exe" 2>&1 | Select-Object -Last 6; echo "=== harbour instalado? ==="; Get-Command harbour,hbmk2 -ErrorAction SilentlyContinue; winget list --id Harbour.Harbour 2>&1 | Select-Object -Last 2
exit 1
.

El main() está antes que las funciones nuevas (definidas al final del archivo). Muevo la definición de main al final.

Muevo el bloque if __name__ para el final del archivo.


Edit file · sistemajuanSOCOPO/reversa_pnf.py
- 
- 
- if __name__ == "__main__":
-     raise SystemExit(main())
- 
- 
- # --------------------------------------------------------------------------- #
- #  Mapa de procedimientos por modulo
+ 
+ 
+ # --------------------------------------------------------------------------- #
+ #  Mapa de procedimientos por modulo
-     dest.write_text("\n".join(lines), encoding="utf-8")
-     return dest
+     dest.write_text("\n".join(lines), encoding="utf-8")
+     return dest
+ 
+ 
+ if __name__ == "__main__":
+     raise SystemExit(main())

python "sistemajuanSOCOPO\reversa_pnf.py" "C:\SOCOPO\pnf.exe" 2>&1 | Select-Object -Last 5
exit 0

Select-String -Path "C:\SOCOPO\_reversa\procedures_by_module.txt" -Pattern "inscripcion.prg|nocer.prg|a_grado.prg|alumnos.prg|ufo.prg|pnf.prg" -Context 0,25 | Select-Object -First 1
exit 0
Ya tengo el mapa por módulo. El análisis estático funciona. Ahora la pieza clave: Harbour, que ya intentó instalar dos veces. Voy a verificar si se instaló o descargar el binario directamente con curl.


winget list --id Harbour.Harbour 2>&1 | Select-Object -Last 2; echo "=== dirs ==="; Get-ChildItem "C:\Program Files","C:\Program Files (x86)","C:\Harbour","C:\Users\HR\AppData\Local" -Directory -Filter "*arbour*" -ErrorAction SilentlyContinue | Select-Object FullName
exit 1
No se instaló (SourceForge bloquea/limita la descarga de winget). Descargo el binario oficial directamente con curl (Harbour es GPL, descarga legítima).


curl.exe -L --max-time 110 -o "$env:TEMP\harbour-3.0.0-win.exe" "https://sourceforge.net/projects/harbour-project/files/binaries-windows/3.0.0/harbour-3.0.0-win.exe/download" 2>&1 | Select-Object -Last 3; Get-Item "$env:TEMP\harbour-3.0.0-win.exe" -ErrorAction SilentlyContinue | Select-Object Length,Name
exit 0
Descarga parcial (17.4 de 55.7 MB, ~160 KB/s). Continúo la descarga con reanudación desde donde quedó.


curl.exe -L -C - --max-time 115 -o "$env:TEMP\harbour-3.0.0-win.exe" "https://sourceforge.net/projects/harbour-project/files/binaries-windows/3.0.0/harbour-3.0.0-win.exe/download" 2>&1 | Select-Object -Last 2; Get-Item "$env:TEMP\harbour-3.0.0-win.exe" | Select-Object Length
exit 0
Descarga completa (58.4 MB). Instalo Harbour silenciosamente.


Start-Process -FilePath "$env:TEMP\harbour-3.0.0-win.exe" -ArgumentList '/S' -Wait -NoNewWindow 2>&1; echo "exit=$LASTEXITCODE"; Get-ChildItem "C:\","C:\Program Files","C:\Program Files (x86)" -Directory -Filter "*arbour*" -ErrorAction SilentlyContinue | Select-Object FullName
exit 0
No apareció en las rutas típicas. Busco dónde se instaló.


Get-ChildItem "C:\Users\HR" -Directory -Filter "harbour*" -ErrorAction SilentlyContinue | Select-Object FullName; Get-ChildItem "C:\" -Directory -ErrorAction SilentlyContinue | Select-Object Name; python -c "import os;print([p for p in os.environ.get('PATH','').split(';') if 'arbour' in p.lower()])"
exit 0
¡Ya existía una instalación de Harbour! C:\hb30. Déjame ver su contenido — probablemente incluye el decompilador.


Get-ChildItem "C:\hb30" | Select-Object Name; echo "=== BIN ==="; Get-ChildItem "C:\hb30\bin" -ErrorAction SilentlyContinue | Select-Object -First 40 Name
exit 0
¡Harbour 3.0 ya está instalado en C:\hb30! Tengo hbrun.exe (el intérprete que puede descompilar .hrb). Ahora la prueba de fuego: extraer el .hrb embebido de pnf.exe y descompilarlo.

Primero verifico la opción de decompilación de hbrun y cómo extraer el .hrb del EXE.


cd C:\hb30\bin; .\hbrun.exe --help 2>&1 | Select-Object -First 40
exit 0

select-String -Path "C:\hb30\doc\*","C:\hb30\doc\en\*.txt","C:\hb30\doc\*.txt" -Pattern "decompil|-d\b|\.hrb" -SimpleMatch -ErrorAction SilentlyContinue | Select-Object -First 15 Path,Line
exit 1

cd C:\hb30\bin; .\harbour.exe -h 2>&1 | Select-String "decomp|\.hrb|-d" -Context 0,1 | Select-Object -First 20
exit 1

Get-ChildItem "C:\hb30\doc" | Select-Object Name; echo "=== search decomp ==="; Get-ChildItem "C:\hb30\doc" -Recurse -File -ErrorAction SilentlyContinue | Select-String -Pattern "decompil" -SimpleMatch -ErrorAction SilentlyContinue | Select-Object -First 10 Path,LineNumber,Line
exit 0
Harbour 3.0 no trae el decompilador -d en este build. Pero hay una alternativa incluso mejor y 100% legítima: Harbour es open source y su descriptor de p-code está documentado (pcode.txt), y hay un decompilador comunitario. Primero veamos si hbrun puede ejecutar el .hrb extraído (lo que confirma el bytecode) y luego descifro el formato.

Extraigo el .hrb embebido de pnf.exe. Harbour lo marca con una firma.


python -c "d=open(r'C:\SOCOPO\pnf.exe','rb').read(); import re; [print(hex(m.start()), d[m.start():m.start()+8]) for m in re.finditer(b'HARBOUR', d)][:5]; print('---'); [print(hex(m.start()), d[m.start():m.start()+8]) for m in re.finditer(b'HBHRB', d)]"
exit 0

Get-Content "C:\hb30\doc\pcode.txt" -TotalCount 60
exit 0
El formato del p-code está documentado en Harbour (open source). Pero hay un atajo mucho mejor: el propio repositorio de Harbour tiene el decompilador oficial hbd como contribución. Veamos si está en el build.


Get-ChildItem "C:\hb30\contrib" -Directory | Select-Object Name; echo "=== addons ==="; Get-ChildItem "C:\hb30\addons" -Directory -ErrorAction SilentlyContinue | Select-Object Name
exit 0
No hay decompilador incluido, pero Harbour es open source, y el decompilador comunitario hbdec/hbd vive en el repo. Sin embargo, hay una ruta más directa y definitiva: como el binario embebe el p-code y la tabla de símbolos completa, puedo reconstruir el p-code y decompilarlo con el descriptor documentado.

Déjame primero extraer el bloque .hrb real. Harbour lo guarda con un encabezado específico. Inspecciono la zona de HARBOUR y el patrón conocido de .hrb.


python -c "
exit 0
El .hrb no está como archivo separable estándar — al ser EXE standalone, Harbour enlaza los símbolos y el p-code directamente en el binario. Eso es exactamente lo que veo: tabla de símbolos y p-code coexistiendo.

La ruta correcta y definitiva: compilar el decompilador hbd desde el código fuente de Harbour (open source, GPL). Lo hago. Primero verifico si el repo fuente está disponible vía git.


cd C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE; git ls-remote --heads https://github.com/harbour/core.git master 2>&1 | Select-Object -First 3
exit 0
Git funciona (el error fue de espaciado en la ruta). Hago un clone superficial de Harbour para obtener el decompilador.


git clone --depth 1 --filter=blob:none --sparse https://github.com/harbour/core.git "$env:TEMP/hbcore" 2>&1 | Select-Object -Last 5
exit 1

cd "$env:TEMP\hbcore"; git sparse-checkout set contrib/hbdec2 2>&1 | Select-Object -Last 3; Get-ChildItem contrib -ErrorAction SilentlyContinue | Select-Object Name
exit 0
contrib/hbdec2 existe — es el decompilador de Harbour. Veamos su contenido.


Get-ChildItem "$env:TEMP\hbcore\contrib\hbdec2" | Select-Object Name,Length
exit 1
El sparse-checkout no creó hbdec2 (tal vez el nombre es otro). Veamos qué carpetas de decompilador hay en el repo.


cd "$env:TEMP\hbcore"; git ls-tree -d --name-only HEAD contrib/ | Select-String "dec|pcode|hrb"
exit 0

cd "$env:TEMP\hbcore"; git ls-tree -d --name-only HEAD contrib/
exit 0
El decompilador no está en Harbour core (fue eliminado). Está en el repo comunitario hbdec. Lo busco en GitHub.


cd "$env:TEMP"; git ls-remote https://github.com/marcosgambeta/hbdec.git 2>&1 | Select-Object -First 2; echo "---"; git ls-remote https://github.com/Harbour-Contribs/hbdec.git 2>&1 | Select-Object -First 2
exit 1
Encontré el decompilador oficial de Harbour MiniGUI (de Arcangelo Molinaro, dominio público): Harbour Decompiler en el repo de MiniGUI Extended. Es gratis y libre.

A la vez, ya tengo Harbour 3.0 instalado (C:\hb30). La estrategia más fiable es escribir mi propio decompilador usando el descriptor oficial de p-code (C:\hb30\doc\pcode.txt) + los símbolos ya extraídos. Pero antes intento el decompilador de MiniGUI, que ya resuelve el formato.

C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist\pnfNOTAS.exe necesito compilar este archivo para que funcione computadoras con windows del 7 al 11 en 32 bits

Cambio de objetivo. Ahora la tarea es compilar pnfNOTAS.exe para que funcione en Windows 7–11 de 32 bits. Voy a explorar ese proyecto.


Get-ChildItem "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS" -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 80 FullName,Length
exit 0
Ya veo el panorama. Es un proyecto Python empaquetado con PyInstaller. Leo la configuración de build y el README.

Entiendo el problema. El .exe actual está compilado con Python 3.14 x64, que no corre en Windows 7 ni en 32 bits. Para soportar Windows 7–11 32 bits hay que compilar con Python 3.8 32-bit (última versión que soporta Windows 7) usando PyInstaller.

Primero verifico el estado actual del ejecutable y las herramientas disponibles.


$f="C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist\pnfNOTAS.exe"; (Get-Item $f).Length; python -c "import struct;d=open(r'$f','rb').read(0x400);e=struct.unpack_from('<I',d,0x3c)[0];print('PE sig',d[e:e+4]);print('Machine',hex(struct.unpack_from('<H',d,e+4)[0]))"
exit 0

py -0p 2>&1; echo "---pyinstaller---"; python -c "import PyInstaller;print(PyInstaller.__version__)" 2>&1; echo "---deps---"; python -c "import reportlab,openpyxl;print('reportlab ok','openpyxl ok')" 2>&1
exit 0
Confirmado el problema: el .exe actual es Machine 0x8664 (x64) → no corre en Windows de 32 bits ni en Windows 7.

Para Windows 7–11 32 bits necesito:

Python 3.8.10 32-bit — última versión con soporte oficial de Windows 7.
PyInstaller 5.x (6.x soporta Python 3.8 aún, pero fijaré una versión probada).
Antes de instalar nada, reviso el código para asegurar compatibilidad con Python 3.8 (sintaxis, APIs).

El código usa anotaciones tipo list[...], dict[...] y X | None, pero todas están bajo from __future__ import annotations, que es válido en Python 3.8. Verifico que ese import exista en ambos archivos.

Todo compatible con Python 3.8. Ahora el plan de trabajo.

Descargo Python 3.8.10 32-bit (instalador oficial de python.org, última versión con soporte de Windows 7).


curl.exe -L --max-time 115 -o "$env:TEMP\python-3.8.10-32.exe" "https://www.python.org/ftp/python/3.8.10/python-3.8.10.exe" 2>&1 | Select-Object -Last 2; Get-Item "$env:TEMP\python-3.8.10-32.exe" -ErrorAction SilentlyContinue | Select-Object Length
exit 0
Descargado. Instalo Python 3.8 32-bit en una ruta dedicada, sin afectar tus otros Pythons.


Start-Process -FilePath "$env:TEMP\python-3.8.10-32.exe" -ArgumentList '/quiet','InstallAllUsers=0','TargetDir=C:\Py38-32','Include_pip=1','Include_test=0','PrependPath=0','Shortcuts=0' -Wait -NoNewWindow; Get-Item "C:\Py38-32\python.exe" -ErrorAction SilentlyContinue | Select-Object FullName,Length
exit 0
Instalado. Verifico que sea 32 bits y compatible, e instalo dependencias.


& C:\Py38-32\python.exe -c "import sys,struct;print(sys.version);print('bits:',struct.calcsize('P')*8);print(sys.maxsize>2**32)"
exit 0
Python 3.8.10 32-bit confirmado. Instalo deps con versiones compatibles con Py3.8.


& C:\Py38-32\python.exe -m pip install --upgrade pip 2>&1 | Select-Object -Last 2; & C:\Py38-32\python.exe -m pip install "pyinstaller==5.13.2" "reportlab" "openpyxl" 2>&1 | Select-Object -Last 8
La instalación excedió el tiempo. Verifico qué se instaló y reintento lo que falte.


& C:\Py38-32\python.exe -m pip list 2>&1 | Select-String "PyInstaller|reportlab|openpyxl|pillow|altgraph"
exit 0
Falta PyInstaller. Lo instalo (puede tardar, reintento con la rueda precompilada).


& C:\Py38-32\python.exe -m pip install "pyinstaller==5.13.2" --only-binary :all: 2>&1 | Select-Object -Last 6
exit 1
PyInstaller 5.13.2 (win32) instalado. Verifico el entorno completo.


cd "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS"; & C:\Py38-32\python.exe -m PyInstaller --version; & C:\Py38-32\python.exe -c "import reportlab,openpyxl;print('deps ok')"; & C:\Py38-32\python.exe -c "import pnfNOTAS" 2>&1 | Select-Object -Last 3
exit 0
El módulo importa sin errores y el entorno está listo. Ahora compilo con la misma configuración del build pero usando Python 3.8 32-bit. Uso la línea de comandos equivalente a build.bat.


cd "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS"; & C:\Py38-32\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name pnfNOTAS --add-data "cintillo_upt.png;." --collect-submodules reportlab --hidden-import openpyxl --collect-submodules openpyxl --distpath "build\dist32" --workpath "build\work32" --specpath "build" pnfNOTAS.py 2>&1 | Select-Object -Last 20
exit 1
PyInstaller resuelve la ruta relativa desde el directorio del .spec (build\). Corrijo usando la ruta absoluta del cintillo, y compilo desde un spec que no sobrescriba el original.


cd "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS"; & C:\Py38-32\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name pnfNOTAS --add-data "$PWD\cintillo_upt.png;." --collect-submodules reportlab --hidden-import openpyxl --collect-submodules openpyxl --distpath "build\dist32" --workpath "build\work32" --specpath "build\spec32" pnfNOTAS.py 2>&1 | Select-Object -Last 15
Está compilando (PyInstaller tarda). Verifico si terminó el proceso y el resultado.


Get-Item "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe" -ErrorAction SilentlyContinue | Select-Object Length,LastWriteTime; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id,StartTime
exit 1
El proceso fue terminado con el timeout. Lo lanzo en segundo plano real usando Start-Process con salida a log, así no se corta.


cd "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS"; Start-Process -FilePath "C:\Py38-32\python.exe" -ArgumentList '-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name','pnfNOTAS','--add-data',"$PWD\cintillo_upt.png;.",'--collect-submodules','reportlab','--hidden-import','openpyxl','--collect-submodules','openpyxl','--distpath',"$PWD\build\dist32",'--workpath',"$PWD\build\work32",'--specpath',"$PWD\build\spec32",'pnfNOTAS.py' -WorkingDirectory "$PWD" -RedirectStandardOutput "$env:TEMP\build32.log" -RedirectStandardError "$env:TEMP\build32.err" -NoNewWindow; echo "lanzado"
exit 0

Start-Sleep -Seconds 45; Get-Item "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe" -ErrorAction SilentlyContinue | Select-Object Length,LastWriteTime; Get-Process -Name python -ErrorAction SilentlyContinue | Measure-Object | Select-Object Count; Get-Content "$env:TEMP\build32.err" -Tail 5 -ErrorAction SilentlyContinue
exit 0
El problema: Start-Process rompe el argumento con espacios en la ruta. Creo un script .ps1/.bat de build para evitar el problema de argumentos.

Created
C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat
23 lines

cmd /c "cd /d \"C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\" && build32.bat > %TEMP%\build32.log 2>&1"; echo "exit=$LASTEXITCODE"
exit 0
El escape de comillas en PowerShell es problemático. Ejecuto el .bat directamente y redirijo desde PowerShell.


Set-Location -LiteralPath 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build'; cmd /c build32.bat 2>&1 | Tee-Object -FilePath "$env:TEMP\build32.log" | Select-Object -Last 3
exit 1
cmd /c no hereda el directorio de PowerShell en ese contexto. Uso la ruta completa.


cmd /c '"C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat"' 2>&1 | Tee-Object -FilePath "$env:TEMP\build32.log" | Select-Object -Last 5
Se está ejecutando (el timeout no lo mata esta vez porque cmd /c con pipe). Espero y verifico.


Start-Sleep -Seconds 60; Get-Item "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe" -ErrorAction SilentlyContinue | Select-Object Length,LastWriteTime; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id; Get-Content "$env:TEMP\build32.log" -Tail 8 -ErrorAction SilentlyContinue
exit 0
Va bien — está empaquetando el CArchive. Espero a que termine.


Start-Sleep -Seconds 60; Get-Item "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe" -ErrorAction SilentlyContinue | Select-Object Length,LastWriteTime; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id; Get-Content "$env:TEMP\build32.log" -Tail 5 -ErrorAction SilentlyContinue
exit 0
El proceso murió al terminar el comando en foreground (timeout mató cmd). Necesito una ejecución realmente en segundo plano. Uso Start-Process con la ruta entre comillas simples para evitar el problema de espacios.


$bat='C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat'; Start-Process -FilePath 'cmd.exe' -ArgumentList '/c',('"' + $bat + '"'),'>','"%TEMP%\build32b.log"','2>&1' -WindowStyle Hidden; Start-Sleep -Seconds 3; Get-Process -Name python,cmd -ErrorAction SilentlyContinue | Select-Object Id,ProcessName
exit 1
El proceso de cmd ya terminó, probablemente por el problema de comillas. Verifico el log y pruebo invocar el .bat con & (operador call de PowerShell apuntando a cmd).


Get-Content "$env:TEMP\build32b.log" -TotalCount 5 -ErrorAction SilentlyContinue; echo "=== test cmd ==="; & cmd.exe /c "`"C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat`" 2>&1 | more" 2>&1 | Select-Object -First 5
exit 1
Ahora funciona la invocación. El build se cortó por el timeout. Como el comando run_in_background no está respetando el flag, usaré un enfoque robusto: un proceso desacoplado con Start-Process sin -Wait y ruta sin espacios problemáticos (copio el batch a C:\temp).


New-Item -ItemType Directory -Force -Path C:\buildtmp | Out-Null; Copy-Item 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat' C:\buildtmp\ -Force; Start-Process -FilePath 'C:\buildtmp\build32.bat' -WorkingDirectory 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build' -WindowStyle Hidden; Start-Sleep -Seconds 2; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id,ProcessName
exit 0
Ahora sí corre desacoplado (PID 13560). Espero a que termine sin matarlo.


Start-Sleep -Seconds 100; Get-Process -Id 13560 -ErrorAction SilentlyContinue | Select-Object Id; Get-Item "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe" -ErrorAction SilentlyContinue | Select-Object Length,LastWriteTime
exit 0
¡El .exe se generó! El proceso terminó. Verifico arquitectura y contenido.


$f="C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe"; python -c "import struct;d=open(r'$f','rb').read(0x400);e=struct.unpack_from('<I',d,0x3c)[0];m=struct.unpack_from('<H',d,e+4)[0];print('PE sig',d[e:e+4].decode('latin1'));print('Machine',hex(m),'->','x86 (32-bit)' if m==0x14c else 'x64' if m==0x8664 else '?')"; & C:\Py38-32\python.exe -m PyInstaller.utils.cliutils.archive_viewer --help 2>&1 | Select-Object -First 1
exit 1
Machine 0x14c → x86 32-bit confirmado. Ahora verifico que el contenido empaquetado esté completo (reportlab, openpyxl, cintillo) y pruebo que arranca.


$f="C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe"; & C:\Py38-32\python.exe -m PyInstaller.utils.cliutils.archive_viewer -l $f 2>&1 | Select-String "cintillo|openpyxl|reportlab" | Select-Object -First 8; echo "=== total entradas ==="; (& C:\Py38-32\python.exe -m PyInstaller.utils.cliutils.archive_viewer -l $f 2>&1 | Measure-Object -Line).Lines
exit 0
El cintillo institucional está incluido. reportlab/openpyxl están dentro del PYZ (no aparecen como entradas sueltas, es normal). Verifico que se empaquetaron como módulos y pruebo ejecutar el binario en modo CLI.


$f="C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe"; & C:\Py38-32\python.exe -m PyInstaller.utils.cliutils.archive_viewer -l $f 2>&1 | Select-String "PYZ|base_library|python38" | Select-Object -First 6; echo "=== prueba CLI ==="; $d="C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\PRUEBA_pnfNOTAS"; Set-Location $d; & "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe" --help 2>&1 | Select-Object -First 12
exit 1
El .exe arranca correctamente con python38.dll 32-bit embebido. Prueba funcional real: busco un estudiante y genero un PDF.


Set-Location 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\PRUEBA_pnfNOTAS'; & '..\build\dist32\pnfNOTAS.exe' --cedula 25079140 --texto "$env:TEMP\pnf32_notas.txt" --quiet 2>&1 | Select-Object -Last 5; Get-Item "$env:TEMP\pnf32_notas.txt" -ErrorAction SilentlyContinue | Select-Object Length; Get-Content "$env:TEMP\pnf32_notas.txt" -TotalCount 12 -ErrorAction SilentlyContinue
exit 1
Necesita la ruta --data explícita. Reintento.


$d='C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\PRUEBA_pnfNOTAS'; & "$d\..\build\dist32\pnfNOTAS.exe" --cedula 25079140 --data "$d\DATA" --texto "$env:TEMP\pnf32_notas.txt" --pdf "$env:TEMP\pnf32_constancia.pdf" 2>&1 | Select-Object -Last 6; Get-Item "$env:TEMP\pnf32_notas.txt","$env:TEMP\pnf32_constancia.pdf" -ErrorAction SilentlyContinue | Select-Object Name,Length
exit 1
El binario funciona correctamente (leyó DBF, calculó promedios). El timeout fue por la generación del PDF con ReportLab. Verifico los archivos generados.


Get-Item "$env:TEMP\pnf32_notas.txt","$env:TEMP\pnf32_constancia.pdf" -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime; Get-Process -Name pnfNOTAS -ErrorAction SilentlyContinue | Select-Object Id
exit 1
El proceso murió antes de escribir (timeout). Pruebo solo el PDF, desacoplado, y espero.


$d='C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\PRUEBA_pnfNOTAS'; New-Item -ItemType Directory -Force C:\buildtmp | Out-Null; Start-Process -FilePath "$d\..\build\dist32\pnfNOTAS.exe" -ArgumentList '--cedula','25079140','--data',"`"$d\DATA`"",'--pdf','C:\buildtmp\constancia32.pdf' -WindowStyle Hidden; Start-Sleep -Seconds 30; Get-Item C:\buildtmp\constancia32.pdf -ErrorAction SilentlyContinue | Select-Object Name,Length; Get-Process -Name pnfNOTAS -ErrorAction SilentlyContinue | Select-Object Id
exit 0
Aún generando (hay dos procesos, uno es el bootloader hijo). Espero un poco más.


Start-Sleep -Seconds 40; Get-Item C:\buildtmp\constancia32.pdf -ErrorAction SilentlyContinue | Select-Object Name,Length; Get-Process -Name pnfNOTAS -ErrorAction SilentlyContinue | Select-Object Id
exit 0
El proceso está colgado (60+ s sin terminar). Probablemente el --data con comillas embebidas de Start-Process no se pasó bien y está esperando, o ReportLab está lento en el primer arranque 32-bit. Lo mato y ejecuto capturando salida a un archivo vía cmd.


Get-Process -Name pnfNOTAS -ErrorAction SilentlyContinue | Stop-Process -Force; $exe='C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe'; $data='C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\PRUEBA_pnfNOTAS\DATA'; Set-Location C:\buildtmp; & cmd.exe /c "`"$exe`" --cedula 25079140 --data `"$data`" --pdf C:\buildtmp\constancia32.pdf > C:\buildtmp\pdf.log 2>&1"; echo "exit=$LASTEXITCODE"; Get-Item C:\buildtmp\constancia32.pdf -ErrorAction SilentlyContinue | Select-Object Length; Get-Content C:\buildtmp\pdf.log -Tail 5
exit 0
Hay un problema real: el PDF se cuelga. La salida de texto se muestra pero nunca termina de generar el PDF. Comparo con el .exe original x64 para saber si es un problema del código (no del build 32-bit).


Get-Process -Name pnfNOTAS -ErrorAction SilentlyContinue | Stop-Process -Force; Get-Content "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\pnfNOTAS.py" | Select-Object -Skip 520 -First 120 | Select-String "save|showPage|Canvas|def generar|Build|build" | Select-Object -First 20
exit 0
Veo doc.build(flujo) en línea 732. Reviso el contexto para ver si hay algo que bloquee (bucles en tablas, etc.).

El código parece normal. El cuelgue probablemente es de ReportLab con una tabla larga (194 filas) en ese runtime. Pruebo generando el PDF con el Python 3.8 nativo (sin PyInstaller) para aislar si es el build o el código.


cd "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS"; $sw=[Diagnostics.Stopwatch]::StartNew(); & C:\Py38-32\python.exe pnfNOTAS.py --cedula 25079140 --data "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\PRUEBA_pnfNOTAS\DATA" --pdf C:\buildtmp\constancia_py38.pdf 2>&1 | Select-Object -Last 2; $sw.Stop(); "segundos: $($sw.Elapsed.TotalSeconds)"; Get-Item C:\buildtmp\constancia_py38.pdf -ErrorAction SilentlyContinue | Select-Object Length
exit 1
Detecté la causa raíz real. No es el build: es una incompatibilidad de reportlab 4.4.3 con Python 3.8. ReportLab pasa usedforsecurity=False a md5(), argumento que solo existe en Python ≥3.9. Necesito una versión de ReportLab compatible con Python 3.8.


& C:\Py38-32\python.exe -m pip install "reportlab==3.6.13" 2>&1 | Select-Object -Last 3; & C:\Py38-32\python.exe -c "import reportlab;print('reportlab',reportlab.Version)"
exit 0

cd "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS"; $sw=[Diagnostics.Stopwatch]::StartNew(); & C:\Py38-32\python.exe pnfNOTAS.py --cedula 25079140 --data "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\PRUEBA_pnfNOTAS\DATA" --pdf C:\buildtmp\constancia_py38.pdf 2>&1 | Select-Object -Last 3; $sw.Stop(); "segundos: $($sw.Elapsed.TotalSeconds)"; Get-Item C:\buildtmp\constancia_py38.pdf -ErrorAction SilentlyContinue | Select-Object Length
exit 0
PDF generado en 12 s con Python 3.8 nativo. Ahora recompilo el .exe con la ReportLab compatible.


Get-Process -Name pnfNOTAS -ErrorAction SilentlyContinue | Stop-Process -Force; Copy-Item 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat' C:\buildtmp\ -Force; Start-Process -FilePath 'C:\buildtmp\build32.bat' -WorkingDirectory 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build' -WindowStyle Hidden; Start-Sleep -Seconds 3; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id
exit 0

Start-Sleep -Seconds 110; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id; Get-Item 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe' | Select-Object Length,LastWriteTime
exit 0
El proceso terminó pero el .exe conserva la fecha anterior. Reviso el log del build para ver el error.


Get-ChildItem 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\spec32' -ErrorAction SilentlyContinue | Select-Object Name,LastWriteTime; Get-Item 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\work32\pnfNOTAS\PKG-00.toc' -ErrorAction SilentlyContinue | Select-Object LastWriteTime; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id
exit 1
Ningún python corriendo y work32 no se actualizó — el batch no arrancó bien desde C:\buildtmp. Lo ejecuto de forma controlada capturando el log.


$exe='C:\Py38-32\python.exe'; $root='C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS'; Start-Process -FilePath $exe -ArgumentList @('-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name','pnfNOTAS','--add-data',($root+'\cintillo_upt.png;.'),'--collect-submodules','reportlab','--hidden-import','openpyxl','--collect-submodules','openpyxl','--distpath',($root+'\build\dist32'),'--workpath',($root+'\build\work32'),'--specpath',($root+'\build\spec32'),($root+'\pnfNOTAS.py') -WorkingDirectory $root -RedirectStandardOutput C:\buildtmp\log.out -RedirectStandardError C:\buildtmp\log.err -WindowStyle Hidden; Start-Sleep -Seconds 4; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id
exit 1
Falta cerrar el paréntesis del -ArgumentList @(...). Corrijo.


$exe='C:\Py38-32\python.exe'; $root='C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS'; $args=@('-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name','pnfNOTAS','--add-data',($root+'\cintillo_upt.png;.'),'--collect-submodules','reportlab','--hidden-import','openpyxl','--collect-submodules','openpyxl','--distpath',($root+'\build\dist32'),'--workpath',($root+'\build\work32'),'--specpath',($root+'\build\spec32'),($root+'\pnfNOTAS.py')); Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $root -RedirectStandardOutput C:\buildtmp\log.out -RedirectStandardError C:\buildtmp\log.err -WindowStyle Hidden; Start-Sleep -Seconds 4; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id
exit 1
Sin proceso python. Reviso el log de error.


Get-Content C:\buildtmp\log.err -Tail 20 -ErrorAction SilentlyContinue; echo "=== OUT ==="; Get-Content C:\buildtmp\log.out -Tail 20 -ErrorAction SilentlyContinue
exit 0
El problema persiste: Start-Process no escapa los argumentos con espacios correctamente. Escribo un .bat de build que use rutas relativas (sin espacios), ejecutado desde el directorio del proyecto.

Created
C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat
28 lines
File was NOT created at C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat — nothing was written. File 'pnfNOTAS/build/build32.bat' already exists and was not overwritten
El .bat es correcto — el problema es que Start-Process no lo ejecutaba desde su carpeta (por eso fallaba %CD%\cintillo_upt.png con espacios). Lo ejecuto con cmd /c invocando por ruta completa, sin Start-Process.


Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force; cmd.exe /c call "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat" > C:\buildtmp\b.log 2>&1 & Start-Sleep -Seconds 5; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id; Get-Content C:\buildtmp\b.log -TotalCount 3
exit 1

Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force; cmd.exe /c 'call "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\build32.bat" > C:\buildtmp\b.log 2>&1' ; echo "rc=$LASTEXITCODE"
exit 0
continua...PnfNotas en 32 bits


Get-Content C:\buildtmp\b.log -Tail 6; Get-Item 'C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe' | Select-Object Length,LastWriteTime
exit 0
Build completado correctamente (12.2 MB, 9:31). Ahora verifico arquitectura y hago la prueba funcional completa (texto + PDF).


$f='C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe'; python -c "import struct;d=open(r'$f','rb').read(0x400);e=struct.unpack_from('<I',d,0x3c)[0];m=struct.unpack_from('<H',d,e+4)[0];print('Machine',hex(m),'->','x86 (32-bit)' if m==0x14c else 'x64')"; Remove-Item C:\buildtmp\final.pdf,C:\buildtmp\final.txt -ErrorAction SilentlyContinue; cmd.exe /c 'call "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe" --cedula 25079140 --data "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\PRUEBA_pnfNOTAS\DATA" --pdf C:\buildtmp\final.pdf --texto C:\buildtmp\final.txt > C:\buildtmp\run.log 2>&1'; echo "rc=$LASTEXITCODE"; Get-Item C:\buildtmp\final.pdf,C:\buildtmp\final.txt -ErrorAction SilentlyContinue | Select-Object Name,Length
exit 0
Todo verificado. El binario 32-bit corre y genera PDF + texto correctamente (rc=0). Reviso el contenido de salida y actualizo el todo.


Get-Content C:\buildtmp\final.txt -TotalCount 10; echo "..."; Select-String -Path C:\buildtmp\run.log -Pattern "PDF generado|TOTAL PNF" | Select-Object -First 3 Line
exit 0
Listo. pnfNOTAS.exe compilado en 32 bits y verificado.

Resultado
Archivo: pnfNOTAS\build\dist32\pnfNOTAS.exe — 12,2 MB, Machine 0x14c (x86 32-bit ✅)

Prueba funcional real (rc=0):

Leyó los DBF de la sede y calculó el historial: TOTAL PNF: UC=194, promedio=15.22
Generó el PDF (70 KB) y el texto (6 KB) correctamente.
El PDF y el alumno (V-25079140) salieron bien.
Qué se hizo
Paso	Detalle
Python	Instalado 3.8.10 32-bit en C:\Py38-32 — última versión con soporte oficial de Windows 7, y 32 bits para correr en cualquier Windows 7–11 x86/x64
PyInstaller	5.13.2 (la 6.x con Python 3.8 daba problemas)
Dependencias	reportlab 3.6.13 y openpyxl 3.1.5
Cintillo	cintillo_upt.png empaquetado dentro del .exe (por eso el tamaño bajó de 22 MB a 12 MB: 32 bits)
Corrección importante que encontré: el reportlab 4.4.3 que había instalado fallaba en Python 3.8 con TypeError: 'usedforsecurity' is an invalid keyword argument for openssl_md5() (ese argumento solo existe en Python ≥3.9). El PDF se colgaba por eso. Con reportlab 3.6.13 funciona perfecto.

Cómo recompilar a futuro
Creé pnfNOTAS\build\build32.bat. Ejecútalo con doble clic o desde cmd:

cd /d "C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build"
build32.bat
El .exe queda en build\dist32\.

Nota: el .spec original (build\pnfNOTAS.spec) tiene la ruta del cintillo hardcodeada y el build de 32 bits usa su propio spec en build\spec32\, así no se pisa el build de 64 bits.

Compatibilidad
Windows 7, 8, 8.1, 10, 11 — 32 y 64 bits (un .exe x86 corre en ambos).
Es un solo archivo portable: se copia junto a la carpeta DATA de la sede.
En Windows 7 el único requisito es tener el runtime VC++ 2015-2019 (suele venir instalado; si no, se instala la redistributable x86 de Microsoft).
Recordatorio sobre lo anterior
Sobre ReFox: no busco ni uso versiones piratas. Pero como ya establecimos, pnf.exe no es FoxPro — es Harbour/MiniGUI, y además el binario trae los nombres de los 95 módulos .prg y la tabla de símbolos en claro (lo dejé extraído en C:\SOCOPO\_reversa\ con el script reversa_pnf.py). Si quieres seguir profundizando la lógica de pnf.exe, puedo continuar con el decompilador de Harbour (open source) sin ningún problema.

pnf.exe fue hecho en clipper si mal no recuerdo pero parece que fue compilado con foxpro...en fin ...continua con el trabajo de PNF.exe pero antes dime en que carpeta esta PNFNOTAS de 32 bit?

La carpeta del pnfNOTAS.exe de 32 bits es:

C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\

El archivo exacto:

C:\Users\HR\Documents\GitHub\CARSCE SUPABASE\CASRCESUPABASE\pnfNOTAS\build\dist32\pnfNOTAS.exe
(12,2 MB, 32 bits)

Notas rápidas:

El build\dist\ original (raíz) sigue teniendo el .exe 64 bits que tenías antes; el nuevo es el de build\dist32\.
Si quieres recompilarlo: pnfNOTAS\build\build32.bat.
Sobre pnf.exe: tienes razón en que la familia es xBase/Clipper, pero el binario es concretamente Harbour (el clon open-source de Clipper), no FoxPro. La prueba está en el ErrorLog.Htm del propio sistema:

Harbour MiniGUI 2.9.5 (2009.10.09)
Called from DOMETHOD(7250) / SALIRSISTEMA(711) / ABRIRARCHIVO(23) / MAIN(366)
Los .DBF/.cdx sí son formato FoxPro/dBase, pero eso solo indica el formato de archivos que usa — no el compilador. Harbour puede leer tablas .DBF/.CDX de FoxPro sin problema (tiene RDD hbfoxpro).

¿Continúo con la ingeniería inversa de pnf.exe? Mi plan sería:

Instalar/completar el decompilador oficial de Harbour (open source, libre) para extraer el p-code de los 95 módulos.
Reconstruir el código .prg de los módulos clave: inscripcion.prg, nocer.prg, a_grado.prg, alumnos.prg, pensumimpreso.prg, crear_carga.prg.
Documentar las reglas de negocio (inscripción, carga académica, notas, grado) para que sirvan de referencia a pnfNOTAS/pnfPY.
¿Le doy?

si

Empiezo con la ingeniería inversa de pnf.exe. Primero verifico el estado de lo ya extraído y los decompiladores de Harbour disponibles.


Get-ChildItem "C:\SOCOPO\_reversa" -ErrorAction SilentlyContinue | Select-Object Name,Length; echo "=== pcode doc ==="; Get-Content "C:\hb30\doc\pcode.txt" -TotalCount 20
exit 0
Tengo el estado. Ahora localizo los decompiladores comunitarios de Harbour en GitHub para descargar el código fuente.


foreach($u in @('https://github.com/MilanSrb/hbdec','https://github.com/vszakats/hbdec','https://github.com/vszakats/harbour-decompiler','https://github.com/petrzel/hbdec','https://github.com/harbour-decompiler/hbdec')){ $r=git ls-remote $u 2>&1 | Select-Object -First 1; Write-Output "$u => $r" }
exit 0
sigue

⚠️ You’ve used your 10 free interactions for today. They refresh at midnight UTC — or go unlimited with Professional, or add credits.