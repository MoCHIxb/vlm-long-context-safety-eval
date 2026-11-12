[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('qwen25vl7b','qwen3vl8b','llava7b','gemma3_12b')][string]$Model,
    [Parameter(Mandatory=$true)][string]$Site,
    [ValidateSet('gate','formal','all')][string]$Stage = 'all',
    [switch]$Execute,
    [switch]$RetryErrors
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$env:HF_HOME = Join-Path $repoRoot '.cache\huggingface'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:OMP_NUM_THREADS = '8'
$env:MKL_NUM_THREADS = '8'
$env:TOKENIZERS_PARALLELISM = 'false'
$launchArgs = @('scripts/run_free_history_supplement.py','--model',$Model,'--site',$Site,'--stage',$Stage)
if ($Execute) { $launchArgs += '--execute' }
if ($RetryErrors) { $launchArgs += '--retry-errors' }
Push-Location -LiteralPath $repoRoot
try {
    & (Join-Path $repoRoot '.venv\Scripts\python.exe') @launchArgs
    $exitCode = $LASTEXITCODE
}
finally { Pop-Location }
exit $exitCode
