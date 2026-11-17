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

$dataDir = Join-Path $source 'data'
$requiredDataEntries = @()
if (Test-Path $dataDir -PathType Container) {
    $manifestPath = Join-Path $dataDir 'manifest.lua'
    if (Test-Path $manifestPath -PathType Leaf) {
        $manifestText = [System.IO.File]::ReadAllText($manifestPath, [System.Text.Encoding]::UTF8)
        $manifestMatch = [regex]::Match($manifestText, '(?s)return\s+\[==\[(.*?)\]==\]')
        if (-not $manifestMatch.Success) { throw "No se pudo leer el manifest: $manifestPath" }
        try {
            $manifest = $manifestMatch.Groups[1].Value | ConvertFrom-Json
        }
        catch {
            throw "El manifest no contiene JSON válido: $manifestPath"
        }
        $patchFiles = @($manifest.guide) + @($manifest.db)
        foreach ($fileName in $patchFiles) {
            if (-not ($fileName -is [string]) -or [System.IO.Path]::GetFileName($fileName) -ne $fileName) {
                throw "Nombre de archivo no válido en el manifest: $fileName"
            }
            $dataFile = Join-Path $dataDir $fileName
            if (-not (Test-Path $dataFile -PathType Leaf)) {
                throw "Falta el archivo listado en el manifest: $dataFile"
            }
            $requiredDataEntries += "AskForever/data/$fileName"
        }
        $requiredDataEntries += 'AskForever/data/manifest.lua'
    }
}

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

# Documentos que se copian al zip y enlaces relativos que deben abrirse en GitHub.
$docNames = @(
    'INSTALL_GUIDE.md',
    'GUIA_INSTALACION.md',
    'SECURITY_TRANSPARENCY.md',
    'SEGURIDAD_TRANSPARENCIA.md'
)
$docsDir = Join-Path $repoRoot 'docs'
$docsFull = (Resolve-Path $docsDir).Path
$repoFull = (Resolve-Path $repoRoot).Path
foreach ($docName in $docNames) {
    $docPath = Join-Path $docsDir $docName
    if (-not (Test-Path $docPath)) { throw "No existe $docPath" }
}

# Los enlaces entre los cuatro documentos incluidos siguen siendo relativos;
# el resto se resuelve contra docs/ y apunta a GitHub.
$rewriteDocsLink = [System.Text.RegularExpressions.MatchEvaluator]{
    param($match)
    $target = $match.Groups[1].Value
    if ($target -match '^(https?://|mailto:|#)') { return $match.Value }
    $hashIndex = $target.IndexOf('#')
    if ($hashIndex -ge 0) {
        $pathPart = $target.Substring(0, $hashIndex)
        $anchor = $target.Substring($hashIndex)
    } else {
        $pathPart = $target
        $anchor = ''
    }
    if ((-not $pathPart) -or ($docNames -contains $pathPart)) { return $match.Value }
    $resolved = [System.IO.Path]::GetFullPath((Join-Path $docsFull ($pathPart -replace '/', '\')))
    $relative = $resolved.Substring($repoFull.Length).TrimStart('\') -replace '\\', '/'
    return "](https://github.com/warcrafted-server/AskForever/blob/main/$relative$anchor)"
}

$requiredEntries = @('AskForever/README.txt') + ($docNames | ForEach-Object { "AskForever/docs/$_" }) + $requiredDataEntries
$utf8 = New-Object System.Text.UTF8Encoding -ArgumentList $false

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
        if ($relative -like 'dev/*' -or $relative -eq 'AskForever.toc' -or $relative -eq 'AskForeverDev.toc') {
            return
        }
        $entry = "AskForever/$relative"
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entry, [System.IO.Compression.CompressionLevel]::Optimal)
    }

    $tocEntry = $zip.CreateEntry('AskForever/AskForever.toc', [System.IO.Compression.CompressionLevel]::Optimal)
    $writer = New-Object System.IO.StreamWriter -ArgumentList $tocEntry.Open(), $utf8
    try {
        $writer.Write($publicToc)
    }
    finally {
        $writer.Dispose()
    }

    foreach ($docName in $docNames) {
        $docPath = Join-Path $docsDir $docName
        $docContent = [System.IO.File]::ReadAllText($docPath, $utf8)
        $docContent = [regex]::Replace($docContent, '\]\(([^)]+)\)', $rewriteDocsLink)
        $docEntry = $zip.CreateEntry("AskForever/docs/$docName", [System.IO.Compression.CompressionLevel]::Optimal)
        $docWriter = New-Object System.IO.StreamWriter -ArgumentList $docEntry.Open(), $utf8
        try {
            $docWriter.Write($docContent)
        }
        finally {
            $docWriter.Dispose()
        }
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
    if ($null -ne $check.GetEntry('AskForever/AskForeverDev.toc')) {
        throw "El zip contiene AskForeverDev.toc."
    }
    foreach ($entryName in $requiredEntries) {
        if ($null -eq $check.GetEntry($entryName)) {
            throw "El zip no contiene $entryName."
        }
    }
    if (Test-Path $dataDir -PathType Container) {
        $dataFiles = @(Get-ChildItem -Path $dataDir -Recurse -File | Where-Object { $_.Name -ne '.gitkeep' })
        foreach ($dataFile in $dataFiles) {
            $relative = $dataFile.FullName.Substring($sourceFull.Length).TrimStart('\') -replace '\\', '/'
            if ($null -eq $check.GetEntry("AskForever/$relative")) {
                throw "El zip no contiene AskForever/$relative."
            }
        }
    }
    foreach ($docName in $docNames) {
        $docEntryName = "AskForever/docs/$docName"
        $docEntry = $check.GetEntry($docEntryName)
        $docReader = New-Object System.IO.StreamReader -ArgumentList $docEntry.Open(), $utf8
        try {
            $docContent = $docReader.ReadToEnd()
        }
        finally {
            $docReader.Dispose()
        }
        if ($docContent -match '\]\(img/' -or $docContent -match '\]\(\.\./') {
            throw "El documento $docEntryName conserva enlaces relativos no permitidos."
        }
    }
    $check.Entries | ForEach-Object { Write-Host "  $($_.FullName)" }
}
finally {
    $check.Dispose()
}
