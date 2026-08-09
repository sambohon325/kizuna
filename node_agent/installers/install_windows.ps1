$ErrorActionPreference = "Stop"
$InstallDirectory = Join-Path $env:LOCALAPPDATA "Kizuna"
$Source = Join-Path $PSScriptRoot "KizunaNode.exe"
$Target = Join-Path $InstallDirectory "KizunaNode.exe"

if (-not (Test-Path -LiteralPath $Source)) { throw "KizunaNode.exe must be beside this installer." }
New-Item -ItemType Directory -Force -Path $InstallDirectory | Out-Null
Copy-Item -LiteralPath $Source -Destination $Target -Force
$Action = New-ScheduledTaskAction -Execute $Target -Argument "hive --poll-seconds 3"
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "Kizuna Node" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Kizuna mixed-platform Hive companion" -Force | Out-Null
Write-Host "Kizuna Node installed at $Target. Enroll it in Kizuna before starting the scheduled task."

