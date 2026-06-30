param(
    [int]$Start = 1,
    [int]$Limit = 1,
    [switch]$All,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "YDSL Gamma PPT runner"
Write-Host "Working folder: $RepoRoot"
Write-Host ""

if ([string]::IsNullOrWhiteSpace($env:GAMMA_API_KEY)) {
    $secureKey = Read-Host "Paste your Gamma API key. It will not be saved to a file" -AsSecureString
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    )
    $env:GAMMA_API_KEY = $plainKey.Trim()
}

if ([string]::IsNullOrWhiteSpace($env:GAMMA_API_KEY)) {
    throw "GAMMA_API_KEY is empty."
}

if ($env:GAMMA_API_KEY -notlike "sk-gamma-*") {
    Write-Warning "Gamma API keys usually start with sk-gamma-. Please confirm the key format."
}

$command = @(".\gamma\run_gamma_from_urls.py", "--start", "$Start")
if ($All) {
    Write-Host "Range: from project $Start to the end"
} else {
    $command += @("--limit", "$Limit")
    Write-Host "Range: project $Start, count $Limit"
}
if ($DryRun) {
    $command += "--dry-run"
    Write-Host "Mode: dry-run, no Gamma credits will be used."
} else {
    Write-Host "Mode: live Gamma generation. This may use Gamma credits."
}

Write-Host ""
Write-Host "Command: python $($command -join ' ')"
Write-Host ""

python @command

Write-Host ""
Write-Host "Results file:"
Write-Host "  $RepoRoot\gamma\gamma_results.csv"
Write-Host "PPTX download folder:"
Write-Host "  $RepoRoot\gamma\pptx"
