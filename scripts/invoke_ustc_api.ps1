[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('list-models', 'text-smoke', 'vision-smoke', 'original-core-extensions')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$secretPath = Join-Path $repoRoot '.cache\ustc_api_key.dpapi'
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $secretPath -PathType Leaf)) {
    throw "Encrypted credential not found. Run scripts\save_ustc_api_secret.ps1 first."
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Project virtual environment not found: $python"
}

$encrypted = [System.IO.File]::ReadAllText($secretPath, [System.Text.Encoding]::ASCII).Trim()
$secureKey = ConvertTo-SecureString -String $encrypted
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
$exitCode = 1
try {
    $env:USTC_LLM_API_KEY = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    $env:PYTHONPATH = 'src'
    Push-Location -LiteralPath $repoRoot
    try {
        switch ($Action) {
            'original-core-extensions' {
                & $python 'scripts/generate_formal_v3_extensions.py' '--workers' '4' '--original-core'
            }
            'list-models' {
                & $python 'scripts/check_ustc_api.py' '--list-models'
            }
            'text-smoke' {
                & $python 'scripts/check_ustc_api.py' '--smoke'
            }
            'vision-smoke' {
                & $python 'scripts/check_ustc_api.py' '--vision-smoke'
            }
        }
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}
finally {
    Remove-Item Env:USTC_LLM_API_KEY -ErrorAction SilentlyContinue
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

exit $exitCode
