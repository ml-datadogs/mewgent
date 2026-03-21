# Rebuild ui/dist when UI sources are newer than the last build (avoids stale overlay).
param(
    [Parameter(Mandatory = $true)]
    [string] $ProjectRoot
)

$ErrorActionPreference = "Stop"
$ui = Join-Path $ProjectRoot "ui"
$pkg = Join-Path $ui "package.json"
$distIndex = Join-Path $ui "dist\index.html"

if (-not (Test-Path $pkg)) {
    exit 0
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host '[run.bat] npm not on PATH - using existing ui\dist. Rebuild: cd ui, then npm run build.'
    exit 0
}

if (-not (Test-Path (Join-Path $ui "node_modules"))) {
    Write-Host '[run.bat] ui\node_modules missing - run: cd ui; npm install; npm run build'
    exit 0
}

$needBuild = -not (Test-Path $distIndex)
if (-not $needBuild) {
    $distTime = (Get-Item $distIndex).LastWriteTimeUtc
    $sourceFiles = @()
    foreach ($dir in @((Join-Path $ui "src"), (Join-Path $ui "public"))) {
        if (Test-Path $dir) {
            $sourceFiles += Get-ChildItem -Path $dir -Recurse -File -ErrorAction SilentlyContinue
        }
    }
    foreach ($name in @(
            "index.html", "vite.config.ts", "package.json", "package-lock.json",
            "tsconfig.json", "tsconfig.app.json", "tsconfig.node.json", "eslint.config.js"
        )) {
        $f = Join-Path $ui $name
        if (Test-Path $f) {
            $sourceFiles += Get-Item $f
        }
    }
    $newest = $sourceFiles | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($newest -and $newest.LastWriteTimeUtc -gt $distTime) {
        $needBuild = $true
    }
}

if (-not $needBuild) {
    exit 0
}

Write-Host "Rebuilding web UI (sources newer than ui\dist)..."
Push-Location $ui
try {
    npm run build
    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
}
finally {
    Pop-Location
}
exit 0
