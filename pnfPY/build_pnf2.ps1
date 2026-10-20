# ============================================================================
#  pnfPY - Construir pnf2.exe (portable) y armar la carpeta de prueba.
#
#  Uso:  powershell -ExecutionPolicy Bypass -File build\build_pnf2.ps1
#
#  Genera:
#    build\dist\pnf2.exe        <- ejecutable unico (GUI + CLI)
#    build\PRUEBA_pnf2\         <- carpeta autocontenida lista para probar
#         pnf2.exe
#         datos\...             <- (copia de tus sedes, si existen)
#         datos_institucionales\
#         LEEME.txt
# ============================================================================
$ErrorActionPreference = "Stop"

# Raiz del proyecto = la propia carpeta del script (script en pnfPY\,
# spec en pnfPY\build\pnf2.spec)
$Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Raiz

# En este repo el script vive en pnfPY\ (raiz) y el .spec en pnfPY\build\
# Si el .spec no esta junto al script, se usa la subcarpeta build.
if (Test-Path (Join-Path $Raiz "pnf2.spec")) {
    $Spec = Join-Path $Raiz "pnf2.spec"
} elseif (Test-Path (Join-Path $Raiz "build\pnf2.spec")) {
    $Spec = Join-Path $Raiz "build\pnf2.spec"
} else {
    Write-Host "No se encontro pnf2.spec" -ForegroundColor Red
    exit 1
}

Write-Host "== pnfPY: construyendo pnf2.exe ==" -ForegroundColor Cyan
Write-Host "Raiz: $Raiz"

# 1) Limpiar builds previos
foreach ($d in @("build\dist", "build\work", "dist", "build\__pycache__")) {
    if (Test-Path $d) { Remove-Item -Recurse -Force $d -ErrorAction SilentlyContinue }
}

# 2) Ejecutar PyInstaller con el spec
Write-Host "`n-- PyInstaller --" -ForegroundColor Yellow
python -m PyInstaller $Spec `
    --noconfirm `
    --distpath "build\dist" `
    --workpath "build\work"

if ($LASTEXITCODE -ne 0) {
    Write-Host "FALLO la compilacion." -ForegroundColor Red
    exit 1
}

$exe = Join-Path $Raiz "build\dist\pnf2.exe"
if (-not (Test-Path $exe)) {
    Write-Host "No se genero pnf2.exe" -ForegroundColor Red
    exit 1
}

$mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host "`nOK: $exe ($mb MB)" -ForegroundColor Green

# 3) Armar carpeta de prueba autocontenida
$Prueba = Join-Path $Raiz "build\PRUEBA_pnf2"
if (Test-Path $Prueba) { Remove-Item -Recurse -Force $Prueba }
New-Item -ItemType Directory -Force -Path $Prueba | Out-Null

Copy-Item $exe (Join-Path $Prueba "pnf2.exe") -Force

# Recursos institucionales
$inst = Join-Path $Raiz "datos_institucionales"
if (Test-Path $inst) {
    Copy-Item $inst (Join-Path $Prueba "datos_institucionales") -Recurse -Force
}

# Sedes: copiar SOLO una muestra ligera (o todas) segun exista.
$datos = Join-Path $Raiz "datos"
if (Test-Path $datos) {
    Write-Host "Copiando sedes a la carpeta de prueba (puede tardar)..." -ForegroundColor Yellow
    Copy-Item $datos (Join-Path $Prueba "datos") -Recurse -Force
}

# LEEME
$leeme = @"
pnfPY - PRUEBA (pnf2.exe)
=========================

1) Doble clic en pnf2.exe -> abre la GUI con el SELECTOR DE SEDE.

2) Desde la consola, en esta misma carpeta:
      pnf2.exe sedes
      pnf2.exe entorno
      pnf2.exe estado --sede socopo
      pnf2.exe historial 25079140 --sede socopo

El programa lee la carpeta `datos\` que esta junto a pnf2.exe.
Para una sola sede, coloque `DATA\` junto al exe (se pedira el nombre de la sede).

Carga de notas (planilla cifrada):
      pnf2.exe generar-carga --sede socopo --codigo <UC> --turno D --seccion A --periodo 2025
      pnf2.exe importar-carga <archivo.xlsx> --sede socopo --previa
"@
Set-Content -Path (Join-Path $Prueba "LEEME.txt") -Value $leeme -Encoding UTF8

Write-Host "`nCarpeta de prueba: $Prueba" -ForegroundColor Green
Get-ChildItem $Prueba | Select-Object Name, Length | Format-Table -AutoSize
