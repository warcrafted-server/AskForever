# AskForever — genera el zip del addon para CurseForge
# Uso:  .\scripts\build-release.ps1
# Resultado: release\AskForever-<versión>.zip con solo la carpeta AskForever\ (sin archivos de desarrollo).

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$repoRoot = Split-Path -Parent $PSScriptRoot
$source   = Join-Path $repoRoot "addon\AskForever"
$version  = (Get-Content (Join-Path $repoRoot "VERSION") -Raw).Trim()
$toc      = Join-Path $source "AskForever.toc"

if (-not (Test-Path $toc)) { throw "No existe $toc" }

$tocVersion = (Select-String -Path $toc -Pattern '^## Version:\s*(.+)$').Matches[0].Groups[1].Value.Trim()
if ($tocVersion -ne $version) {
    throw "La versión del .toc ($tocVersion) no coincide con VERSION ($version)."
}

# Todo archivo listado en el .toc debe existir, o el addon cargaría roto.
$missing = Get-Content $toc | Where-Object { $_ -and ($_ -notmatch '^\s*##') } | ForEach-Object {
    $rel = $_.Trim() -replace '/', '\'
    if (-not (Test-Path (Join-Path $source $rel))) { $rel }
}
if ($missing) { throw "Archivos del .toc que no existen: $($missing -join ', ')" }

$outDir = Join-Path $repoRoot "release"
New-Item -ItemType Directory -Force $outDir | Out-Null
$zipPath = Join-Path $outDir "AskForever-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

# Entradas con «/» (Compress-Archive de Windows PowerShell 5.1 usa «\», que rompe zips en otros sistemas).
$zip = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    $sourceFull = (Resolve-Path $source).Path
    Get-ChildItem -Path $source -Recurse -File | Where-Object { $_.Name -ne ".gitkeep" } | ForEach-Object {
        $relative = $_.FullName.Substring($sourceFull.Length).TrimStart('\') -replace '\\', '/'
        $entry = "AskForever/$relative"
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entry, [System.IO.Compression.CompressionLevel]::Optimal)
    }
}
finally {
    $zip.Dispose()
}

Write-Host "Creado: $zipPath"
$check = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
try { $check.Entries | ForEach-Object { Write-Host "  $($_.FullName)" } } finally { $check.Dispose() }
