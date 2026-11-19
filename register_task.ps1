# Registra la tarea programada "hotsale_2026_retail" en el server.
# - Diario a las 09:30
# - Ultima ejecucion: 2026-11-19 09:30 (envia el acumulado completo 09 al 18 de noviembre)
# - Corre aunque el usuario no tenga sesion iniciada (pide la contrasena del usuario de servicio)
#
# Ejecutar UNA vez en el server, en PowerShell como Administrador:
#   powershell -ExecutionPolicy Bypass -File <ruta_del_proyecto>\register_task.ps1

$ErrorActionPreference = 'Stop'

$TaskName    = 'hotsale_2026_retail'
$ProjectRoot = $PSScriptRoot
$Script      = Join-Path $ProjectRoot 'main.ps1'
$RunTime     = '09:30'
$LastRun     = [datetime]'2026-11-19T09:30:00'

if (-not (Test-Path $Script)) { throw "No existe $Script" }

# Primera ejecucion: hoy a las 09:30 si aun no pasa, si no, manana
$FirstRun = [datetime]::Today.Add([timespan]$RunTime)
if ($FirstRun -le (Get-Date)) { $FirstRun = $FirstRun.AddDays(1) }
if ($FirstRun -gt $LastRun) { throw 'La fecha de primera ejecucion ya es posterior al 2026-11-19; no hay nada que programar.' }

$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$Script`"" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At $FirstRun
$Trigger.EndBoundary = $LastRun.AddMinutes(30).ToString('s')

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$Cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message "Contrasena del usuario que ejecutara la tarea"

Register-ScheduledTask `
    -TaskName $TaskName `
    -Description 'Envio diario sell out Pre Buen Fin y Buen Fin 2026 (acumulado 2026-11-09 a ayer, tope 2026-11-18).' `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -User $Cred.UserName `
    -Password $Cred.GetNetworkCredential().Password `
    -RunLevel Highest `
    -Force | Out-Null

$Info = Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
Write-Host "Tarea '$TaskName' registrada."
Write-Host "Proxima ejecucion: $($Info.NextRunTime)"
Write-Host "Ultima ejecucion programada: $LastRun"
