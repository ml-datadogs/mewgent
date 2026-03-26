# Rebuild ui/dist when UI sources changed since last build.
# Uses git tree hash of ui/ to detect content changes reliably (timestamps are
# unreliable after git pull/checkout).
param(
    [Parameter(Mandatory = $true)]
    [string] $ProjectRoot
)

$ErrorActionPreference = "Stop"
$ui = Join-Path $ProjectRoot "ui"
$pkg = Join-Path $ui "package.json"
$distIndex = Join-Path $ui "dist\index.html"
$hashFile = Join-Path $ui "dist\.ui-build-hash"

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
    $currentHash = $null
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $currentHash = git -C $ProjectRoot rev-parse "HEAD:ui" 2>$null
    }
    if ($currentHash) {
        $savedHash = $null
        if (Test-Path $hashFile) {
            $savedHash = (Get-Content $hashFile -Raw).Trim()
        }
        if ($currentHash -ne $savedHash) {
            $needBuild = $true
        }
    } else {
        # Fallback to timestamp comparison when git is unavailable
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
}

if (-not $needBuild) {
    exit 0
}

Write-Host "Rebuilding web UI (sources changed since last build)..."
Push-Location $ui
try {
    npm run build
    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
    # Save the current git tree hash so we can skip rebuild next time
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $builtHash = git -C $ProjectRoot rev-parse "HEAD:ui" 2>$null
        if ($builtHash) {
            $builtHash | Out-File -FilePath $hashFile -Encoding ascii -NoNewline
        }
    }
}
finally {
    Pop-Location
}
exit 0
