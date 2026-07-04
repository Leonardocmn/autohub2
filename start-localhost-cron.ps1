$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$phpCommand = Get-Command php -ErrorAction SilentlyContinue
$php = if ($phpCommand) { $phpCommand.Source } else { $null }
$portablePhp = Join-Path (Split-Path -Parent $root) "tools\php\php.exe"
$cron = Join-Path $root "cron\process_pending.php"
$logDir = Join-Path $root "storage\logs"
$logFile = Join-Path $logDir "localhost-cron.log"

if (!$php -and (Test-Path $portablePhp)) {
    $php = $portablePhp
}

if (!$php) {
    Write-Host "PHP nao encontrado."
    exit 1
}

if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

Write-Host "AutoHub cron local iniciado."
Write-Host "Arquivo: $cron"
Write-Host "Log:     $logFile"
Write-Host "Intervalo: 60 segundos"
Write-Host ""
Write-Host "Pressione Ctrl+C para parar."

while ($true) {
    $started = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    try {
        "[$started] process_pending.php" | Out-File -FilePath $logFile -Append -Encoding utf8
        & $php $cron 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8
    } catch {
        $message = $_.Exception.Message
        "[$started] ERRO: $message" | Out-File -FilePath $logFile -Append -Encoding utf8
    }
    Start-Sleep -Seconds 60
}
