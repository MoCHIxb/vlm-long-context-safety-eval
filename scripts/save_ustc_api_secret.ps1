[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$cacheDir = Join-Path $repoRoot '.cache'
$secretPath = Join-Path $cacheDir 'ustc_api_key.dpapi'

New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
$secureKey = Read-Host 'Enter USTC API Key (input is hidden)' -AsSecureString
if ($secureKey.Length -eq 0) {
    throw 'API Key cannot be empty.'
}

# On Windows, omitting -Key uses DPAPI tied to the current Windows user.
$encrypted = ConvertFrom-SecureString -SecureString $secureKey
[System.IO.File]::WriteAllText($secretPath, $encrypted, [System.Text.Encoding]::ASCII)
Write-Output "Saved Windows-user encrypted credential: $secretPath"
Write-Output 'Plaintext was not printed. The .cache directory is ignored by Git.'
