$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $root ".env"
$localEnvPath = Join-Path $root ".env.localhost"

if (!(Test-Path $envPath)) {
    Copy-Item $localEnvPath $envPath
    Write-Host "Criado .env local usando .env.localhost"
}

$phpCommand = Get-Command php -ErrorAction SilentlyContinue
$php = if ($phpCommand) { $phpCommand.Source } else { $null }
$portablePhp = Join-Path (Split-Path -Parent $root) "tools\php\php.exe"
if (!$php -and (Test-Path $portablePhp)) {
    $php = $portablePhp
}
if (!$php) {
    Write-Host "PHP nao encontrado no PATH."
    Write-Host "Instale com um destes caminhos:"
    Write-Host "  winget install --id PHP.PHP -e"
    Write-Host "ou instale XAMPP/Laragon e rode novamente."
    exit 1
}

Write-Host "AutoHub MVP local em: http://127.0.0.1:8080"
Write-Host "Instalador em:        http://127.0.0.1:8080/install.php"
Write-Host "Cron local separado:  .\start-localhost-cron.ps1"
Write-Host ""
Write-Host "Pressione Ctrl+C para parar."
& $php -S 127.0.0.1:8080 -t (Join-Path $root "public")
