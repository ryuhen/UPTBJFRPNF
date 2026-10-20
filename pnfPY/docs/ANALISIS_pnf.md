# ANÁLIS DE INGENIERÍA INVERSA — `pnf.exe` (Sistema Juan / UPTJFR)

> Documento de trabajo. Resultado del análisis estático del ejecutable legado
> `sistemajuanSOCOPO\pnf.exe` (3.579.799 bytes) y de los archivos `DATA\*.DBF`.
>
> **Herramienta usada:** extracción de cadenas (strings) + inspección de cabeceras
> DBF. REA (`sistemajuanSOCOPO\rea`) queda disponible para un análisis más
> profundo con Ghidra/Hopper, pero para un binario **Harbour/xHarbour + HMG**
> compilado, la vía más productiva es strings + datos (lo que se hizo aquí).

---

## 1. IDENTIFICACIÓN DEL EJECUTABLE

| Dato | Valor |
|---|---|
| Archivo | `pnf.exe` (3.579.799 bytes) |
| Fecha | 2025-06-04 |
| Compilador | **Harbour / xHarbour** (`_hb_vm_*`, `_HB_FUN_*`, `hbvpdf`, `rddsys`) |
| GUI | **HMG** (Harbour MiniGUI) — rutas `c:/hmg/source/h_*.prg` |
| Motor de datos | RDD DBF/CDX (`.dbf` + `.cdx`, también `.ntx`) |
| Reportes | `hbvpdf` (PDF nativo de Harbour) |
| Versión byte DBF | dBase III (`0x03`) |

> **Conclusión clave:** `pnf.exe` **no es un `.exe` nativo de C/C++** que se
> pueda "decompilar" a código legible. Es bytecode de Harbour: los strings
> revelan los **nombres de módulos `.prg`**, funciones y textos de menú, que es
> exactamente lo que se necesita para reconstruir la lógica en Python.

---

## 2. INVENTARIO DE MÓDULOS (nombres `.prg` embebidos)

Cada archivo `.prg` es un módulo del sistema. Estos son **todos** los módulos
propios (los `c:/hmg/...` son de la librería gráfica HMG):

### 2.1 Configuración / institucional
| Módulo | Función |
|---|---|
| `CONFIGURACION.prg` | Parámetros de la sede (universidad, sede, resolución, gaceta, límite75) |
| `AUTORIDADES.prg` | Registro de autoridades |
| `PNF.prg` / `PROGRAMAS_FORMACION.prg` | Programas Nacionales de Formación (carreras) |
| `UFO.prg` | Unidades de Formación / Curriculares (catálogo de UC) |
| `ANO_LECTIVO.prg` | Año / período lectivo |
| `MODALIDAD.prg` | Modalidades de estudio |
| `INDICES.prg` | Reindexado de tablas (CDX) |
| `CARGAR_DATA.prg` | Carga inicial / importación de datos |

### 2.2 Personas
| Módulo | Función |
|---|---|
| `ALUMNOS.prg` | Estudiantes (altas, bajas, cambios) |
| `DOCENTES.prg` | Docentes |
| `C_SEC.prg` / `C_CEDULA.prg` | Cambio de sección / de cédula (documento de identidad) |

### 2.3 Inscripción
| Módulo | Función |
|---|---|
| `INSCRIPCION.prg` | **Inscripción de estudiantes** en unidades curriculares |
| `COMUNITARIO.prg` | Servicio comunitario estudiantil |
| `RANGO.prg` | Rango y posición (orden de mérito) |

### 2.4 Carga académica / docente
| Módulo | Función |
|---|---|
| `CARGA_DOCENTE.prg` | Carga académica del docente |
| `CREAR_CARGA.prg` | **Asignación** de carga (crear carga) |
| `MONITOR_CARGA.prg` | Monitor de carga docente de calificaciones |
| `CERTIFICACIONCCH.prg` | Certificación de Carga Horaria |
| `CERTIFICACIONCDC.prg` | Certificación de Carga (docente) |

### 2.5 Notas
| Módulo | Función |
|---|---|
| `CARGA_DOCENTE.prg` | **Entrega / carga de notas** por el docente |
| `CORRECCION.prg` | Corrección de notas |
| `GLOBALNOTASCERTIFICADAS.prg` | Notas certificadas (global) |
| `CONDUCTA.prg` | Notas de conducta |
| `DISTINCIONES.prg` | Distinciones académicas |

### 2.6 Grado / egreso
| Módulo | Función |
|---|---|
| `A_GRADO.prg` | **Actos de Grado** (definir/configurar fechas de grado) |
| `ACTAGRADO.prg` | Actas de grado |
| `CULMINACION.prg` / `CULMINACIONGRADO.prg` | Culminación de estudios / de grado |
| `CEAG.prg` / `ECAG.prg` / `EEAG.prg` / `OGC.prg` | Certificaciones / egresados de acto de grado |
| `LISTAGRADO.prg` | Listado oficial de graduandos |
| `DG.prg` / `DGC.prg` | Documentos de grado / certificados |
| `NOCER.prg` | (imposición / no certificados) |
| `MIGRACION.prg` | Migración de pensum (estudiantes a plan nuevo) |

### 2.7 Reportes / constancias
| Módulo | Función |
|---|---|
| `R_CE.prg` | Reporte de Constancias de Estudio |
| `R_CN.prg` | Reporte de Constancias de Notas |
| `R_SA.prg` | Reporte de Solventes / Asistencia |
| `RDI.prg` / `RED.prg` / `RYP.prg` | Reportes varios (ingreso / egreso / y período) |
| `PENSUMIMPRESO.prg` | Impresión del pensum de estudio |
| `PROGEN.prg` | Programa / pensum general |

---

## 3. FUNCIONES INTERNAS RELEVANTES (`_HB_FUN_*`)

Extraídas del binario; describen acciones de negocio:

```
ACTAGRADO, ESPERAACTAGRADO, LISTAGRADO, SELECCIONLISTADOGRADO
GENERAR_CONSTANCIA, TRAERCONSTANCIACULMINACION, TRAERNOTASCERTIFICADAS
GLOBALNOTASCERTIFICADAS, PENSUMIMPRESO
IMPRIMIR_ASISTENCIA, IMPRIMIR_CULMINACION, IMPRIMIR_DG, IMPRIMIR_INSCRIPCION,
IMPRIMIR_R_CN, IMPRIMIR_R_SA, IMPRIMIR_SOLVENTES
PROCESAR_A_GRADO, GRABAR_A_GRADO, INICIALIZAR_A_GRADO, TRAER_A_GRADO,
ACTIVAR_A_GRADO, DESACTIVAR_A_GRADO, BORRAR_A_GRADO, VALIDAR_A_GRADO
IMPRESORAS, IMPRESION_NOCER, SELECTORIMPRESION
CREARTABLAACTODEGRADO, CREATABLALECTIVOPENSUM
```

Y funciones de datos por columna (típicas de los `grid` de HMG):
`ALUMNOS_ACTIVO()`, `ALUMNOS_PASAPORTE()`, `ALUMNOS_PROFESIONAL()`,
`ALUMNOS_SITUACION()`, `ALUMNOS_TURNO()`, `AUTORIDADES_CARGO()`,
`AUTORIDADES_SEXO()`, `MODALIDAD_UFO()`, etc.

---

## 4. MENÚ / FLUJO FUNCIONAL (reconstruido)

De los textos de menú (prefijos HMG `Hj`/`dj`) se deduce esta estructura:

```
MENÚ PRINCIPAL
├── Configuración
│   ├── Autoridades
│   ├── Programas Nacionales de Formación (PNF)
│   ├── Unidades Curriculares (UFO)
│   ├── Año Lectivo / Períodos
│   ├── Modalidades de Estudio
│   └── Cargar Datos
├── Estudiantes (Alumnos)
│   ├── Registro de estudiantes
│   ├── Cambio de Documento de Identidad
│   ├── Cambio de Turno y/o Sección
│   └── Registro Histórico de Unidades Curriculares del estudiante
├── Inscripción
│   ├── Inscribir unidades curriculares
│   ├── Alumnos Inscritos por Unidad Curricular / de Formación
│   └── Consulta Detallada de Secciones
├── Carga Académica
│   ├── Crear / Asignar carga
│   ├── Carga Docente
│   ├── Monitor de Carga Docente de Calificaciones
│   └── Certificación de Carga Horaria / Docente
├── Notas
│   ├── Carga de Notas (entrega por docente)
│   ├── Corrección de notas
│   ├── Notas Certificadas / Global
│   └── Conducta / Distinciones
├── Grado
│   ├── Definir / Configurar Actos de Grado
│   ├── Cargar Graduandos
│   ├── Posibles Graduandos / Certificados
│   ├── Documentos de Grado
│   ├── Orden del Reporte Oficial de Graduandos
│   └── Listado de Graduados / Migración de pensum
└── Reportes / Constancias
    ├── Constancias de Estudio
    ├── Constancias de Notas (con calificaciones certificadas)
    ├── Constancia de Inscripción
    ├── Constancia de Culminación
    ├── Solventes / Asistencia
    └── Pensum impreso
```

---

## 5. MODELO DE DATOS (DBF)

### 5.1 Tablas maestras
| Tabla | Contenido |
|---|---|
| `CONFIG.DBF` | Configuración: `UNIVERSIDA`, `SEDE`, `COD_SEDE`, `RESOLUCION`, `GACETA`, `FECHA`, `LECTIVO`, `LIMITE75` |
| `ALM.DBF` | Estudiantes: `A_ID` (cédula), `A_NOMBRE`, `A_APELLIDO`, `A_FINGRESO`, `A_TEL1`, `A_PNF`, `A_PENSUM`, … |
| `UFO.DBF` | Unidades curriculares: `UFO_CLAVE`, `PNF_CODIGO`, `CODIGO`, `UFO_NOMBRE`, `TRAYECTO`, `TRAMO`, `HTA/HTI/HTT`, `UC`, `TIPO` |
| `PNF.DBF` | Programas Nacionales de Formación (carreras) |
| `DCT.DBF` / `DOCENTES` | Docentes |
| `CC.DBF` | Cuentas / control (una de las tablas grandes, 1.6 MB) |
| `A_GRADO.DBF` | Actos de grado |
| `CADG01.DBF` / `CADGC.DBF` | Cadenas / códigos de grado |
| `DGC.dbf` | Documentos de grado (certificados) |

### 5.2 Tablas por período (una por año)
| Patrón | Significado |
|---|---|
| `INS####.DBF` | **Inscripciones** del período regular `####` |
| `INS####P.DBF` | Inscripciones del período "PER" |
| `INS####I.DBF` | Inscripciones **intersemestral** |
| `SEA####.DBF` | **Sesiones de evaluación / asistencia** del período |
| `SEA####P/I.DBF` | Variantes PER / intersemestral |
| `G00########.dbf` | **Graduandos** (fecha `DDMMAAAA`), con `A_IA` (índice académico) y `A_UCAPRO` |

Campos típicos de `INS####`:
`A_ID` (cédula), `CARRERA`, `CODIGO` (UC), `TRAYECTO`, `TRAMO`, `TURNO`
(`D`=Diurno, `F`=Fin de semana), `SECCION`, `ANO` (`2019`/`2019P`),
`NOTA` (`None`=sin cargar, `0`=no cargada/reprobada), `ASISTENCIA`,
`CONDICION`, `TIPO`, `UC`, `BORRAR` (anulación lógica).

> **Regla de negocio confirmada** (ver `BITACORA_pnfNOTAS.md`):
> nota mínima **12** general, **16** para el **Proyecto** (`UFO.TIPO = 'P'`);
> promedio ponderado = `Σ(nota × UC) / Σ(UC)`; la constancia muestra la **última**
> nota por UC (última aprobada si aprobó alguna vez).

---

## 6. EQUIVALENCIA CON EL SISTEMA NUEVO (CARSCE / Supabase)

El repo `CASRCESUPABASE` ya implementa gran parte de esto en web (React + Supabase):

| Legado (`pnf.exe`) | Nuevo (CARSCE) |
|---|---|
| `INSCRIPCION.prg` | `inscripcion`, `cursada`, `cursable`, `inscripcion_seccion` |
| `CREAR_CARGA.prg` / `CARGA_DOCENTE.prg` | `carga_academica`, `perfil_docente`, `seccion`, `v_carga_academica` |
| Notas (`CARGA_DOCENTE`) | `historico_academico`, `cursable_nota` |
| `UFO.prg` | `unidad`, `pensum` |
| `PNF.prg` | `carrera`, `pensum` |
| `A_GRADO.prg` / `LISTAGRADO.prg` | `acto_grado`, `graduando`, RPC `acto_grado_*` |
| Constancias | `DocumentosAdmin.jsx` (Constancia de Carga Académica, Acta de Notas) |

---

## 7. ESTRATEGIA DE REESCRITURA EN PYTHON (multi-sede)

El objetivo es un programa **Python autónomo** que lea las carpetas `DATA` del
sistema legado, pero con **una carpeta por sede**, de modo que un coordinador
pueda trabajar las **cuatro sedes a la vez**:

```
pnfPY\
├── pnf2.py                   # entrada (CLI + GUI Tkinter)
├── core\
│   ├── dbf_reader.py         # lector DBF sin dependencias (reutilizado)
│   ├── sedes.py              # descubrimiento/gestión de las 4 sedes
│   ├── data_store.py         # carga e indexa una sede (ALM, UFO, INS####, CONFIG)
│   ├── inscripcion.py        # inscripción de UC
│   ├── carga_academica.py    # asignación y carga docente
│   ├── notas.py              # entrega/corrección de notas
│   ├── historial.py          # historial + promedio ponderado
│   ├── grado.py              # actos de grado / graduandos
│   └── constancia.py         # PDF de constancias
├── datos\
│   ├── barinas\DATA\
│   ├── barinitas\DATA\
│   ├── pedraza\DATA\
│   └── socopo\DATA\
├── datos_institucionales\    # cintillo_upt.png, logos, bandera
└── docs\ANALIS_pnf.md
```

Cada `datos\<sede>\DATA\` es una **copia/estructura idéntica** de la carpeta
`DATA` de esa sede (mismos nombres de archivo: `ALM.DBF`, `UFO.DBF`,
`INS####.DBF`, `CONFIG.DBF`). El programa **elige la sede** por parámetro
(`--sede barinas`) o desde un selector en la GUI, sin cambiar código.

---

## 8. PRÓXIMOS PASOS

1. [x] Identificar compilador, módulos, menús y modelo de datos.
2. [x] Documentar equivalencia con el sistema nuevo.
3. [ ] Crear la estructura `pnfPY\` y el gestor de sedes.
4. [ ] Portar el lector DBF y el `data_store` multi-sede.
5. [ ] Implementar por módulos: inscripción, carga, notas, grado, constancias.
6. [ ] GUI con **selector de sede** y exportación (PDF/Excel/texto).
