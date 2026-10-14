$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$mmds = Join-Path $root "data\raw\mmds"
$mmdu = Join-Path $root "data\raw\mmdu"
New-Item -ItemType Directory -Force -Path $mmds, $mmdu | Out-Null

$files = @(
    @{
        Url = "https://huggingface.co/datasets/leost233/MMDS/resolve/main/mmds.jsonl?download=true"
        Path = Join-Path $mmds "mmds.jsonl"
    },
    @{
        Url = "https://huggingface.co/datasets/leost233/MMDS/resolve/main/images.zip?download=true"
        Path = Join-Path $mmds "images.zip"
    },
    @{
        Url = "https://huggingface.co/datasets/laolao77/MMDU/resolve/main/benchmark.json?download=true"
        Path = Join-Path $mmdu "benchmark.json"
    },
    @{
        Url = "https://huggingface.co/datasets/laolao77/MMDU/resolve/main/mmdu_pics.zip?download=true"
        Path = Join-Path $mmdu "mmdu_pics.zip"
    }
)

foreach ($file in $files) {
    if (Test-Path -LiteralPath $file.Path) {
        Write-Host "Already present: $($file.Path)"
        continue
    }
    Write-Host "Downloading $($file.Url)"
    Invoke-WebRequest -Uri $file.Url -OutFile $file.Path
}

Write-Host "v2 source downloads are ready."
