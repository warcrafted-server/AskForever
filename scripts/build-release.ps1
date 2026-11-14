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

$tocLines = Get-Content $toc
$tocVersion = (Select-String -Path $toc -Pattern '^## Version:\s*(.+)$').Matches[0].Groups[1].Value.Trim()
if ($tocVersion -ne $version) {
    throw "La versión del .toc ($tocVersion) no coincide con VERSION ($version)."
}

# Todo archivo listado en el .toc debe existir, o el addon cargaría roto.
# Las líneas dev/ son de desarrollo y no van en el zip público.
$missing = $tocLines | Where-Object {
    $_ -and ($_ -notmatch '^\s*##') -and ($_ -notmatch '^\s*dev/')
} | ForEach-Object {
    $rel = $_.Trim() -replace '/', '\'
    if (-not (Test-Path (Join-Path $source $rel))) { $rel }
}
if ($missing) { throw "Archivos del .toc que no existen: $($missing -join ', ')" }

$publicTocLines = $tocLines | Where-Object { $_ -notmatch '^\s*dev/' }
$publicToc = ($publicTocLines -join "`n")
if (-not $publicToc.EndsWith("`n")) { $publicToc += "`n" }

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
        if ($relative -like 'dev/*' -or $relative -eq 'AskForever.toc') {
            return
        }
        $entry = "AskForever/$relative"
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entry, [System.IO.Compression.CompressionLevel]::Optimal)
    }

    $tocEntry = $zip.CreateEntry('AskForever/AskForever.toc', [System.IO.Compression.CompressionLevel]::Optimal)
    $encoding = New-Object System.Text.UTF8Encoding -ArgumentList $false
    $writer = New-Object System.IO.StreamWriter -ArgumentList $tocEntry.Open(), $encoding
    try {
        $writer.Write($publicToc)
    }
    finally {
        $writer.Dispose()
    }
}
finally {
    $zip.Dispose()
}

Write-Host "Creado: $zipPath"
$check = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $badEntries = @($check.Entries | Where-Object { $_.FullName -like '*dev/*' })
    if ($badEntries.Count -gt 0) {
        throw "El zip contiene entradas de desarrollo: $($badEntries.FullName -join ', ')"
    }
    $tocEntry = $check.GetEntry('AskForever/AskForever.toc')
    if ($null -eq $tocEntry) {
        throw "El zip no contiene AskForever/AskForever.toc."
    }
    $reader = New-Object System.IO.StreamReader -ArgumentList $tocEntry.Open()
    try {
        $zipToc = $reader.ReadToEnd()
    }
    finally {
        $reader.Dispose()
    }
    if ($zipToc -match 'DevReport') {
        throw "El .toc del zip menciona DevReport."
    }
    $check.Entries | ForEach-Object { Write-Host "  $($_.FullName)" }
}
finally {
    $check.Dispose()
}
