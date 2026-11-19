# Ejecuta el proceso con el Python del entorno virtual.
# Interprete: variable de entorno HOTSALE_PYTHON o, por defecto, .venv\Scripts\python.exe del proyecto.
# Lo invoca el Programador de tareas (ver register_task.ps1).

$ProjectRoot = $PSScriptRoot
$Python = if ($env:HOTSALE_PYTHON) { $env:HOTSALE_PYTHON } else { Join-Path $ProjectRoot '.venv\Scripts\python.exe' }
$LogDir = Join-Path $ProjectRoot 'log'
$ConsoleLog = Join-Path $LogDir 'main_ps1_console.log'

Set-Location -Path $ProjectRoot
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

if (-not (Test-Path $Python)) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | ERROR | No existe $Python" |
        Out-File -FilePath $ConsoleLog -Append -Encoding utf8
    exit 1
}

# Salida de consola (incluye errores previos al log de Python) se agrega a log\main_ps1_console.log
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | INFO | Inicio main.ps1" |
    Out-File -FilePath $ConsoleLog -Append -Encoding utf8

& $Python (Join-Path $ProjectRoot 'main.py') 2>&1 |
    ForEach-Object { "$_" } |
    Out-File -FilePath $ConsoleLog -Append -Encoding utf8
$ExitCode = $LASTEXITCODE

"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | INFO | Fin main.ps1 (codigo de salida: $ExitCode)" |
    Out-File -FilePath $ConsoleLog -Append -Encoding utf8

exit $ExitCode
