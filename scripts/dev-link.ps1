# AskForever â€” enlace simbÃ³lico de desarrollo
# Uso (sin administrador crea una unión de directorio; con administrador o Modo de desarrollador, un enlace simbólico):
#   .\scripts\dev-link.ps1
#   .\scripts\dev-link.ps1 -AddOnsPath "D:\Juegos\World of Warcraft\_forever_\Interface\AddOns"

param(
    [string]$AddOnsPath = "C:\Wow\World of Warcraft\_forever_\Interface\AddOns"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repoRoot "addon\AskForever"
$toc = Join-Path $source "AskForever.toc"
$devToc = Join-Path $source "AskForeverDev.toc"
$oldTarget = Join-Path $AddOnsPath "AskForever"
$devTarget = Join-Path $AddOnsPath "AskForeverDev"

if (-not (Test-Path $source))   { throw "No existe la carpeta del addon: $source" }
if (-not (Test-Path $AddOnsPath)) { throw "No existe la carpeta AddOns: $AddOnsPath" }
if (-not (Test-Path $toc))      { throw "No existe el .toc del addon: $toc" }

# El .toc se regenera en cada ejecuciÃ³n; mantiene los finales de lÃ­nea del original.
$content = [System.IO.File]::ReadAllText($toc)
$content = $content.Replace('## Title: AskForever', '## Title: AskForever (dev)')
$content = $content.Replace('## Title-esES: AskForever',
                             '## Title-esES: AskForever (desarrollo)')
$content = $content -replace '(?m)^## Version:[^\r\n]*', '## Version: dev'
$content = $content.Replace(
    '## IconTexture: Interface\AddOns\AskForever\Media\Icon',
    '## IconTexture: Interface\AddOns\AskForeverDev\Media\Icon')
$utf8 = New-Object System.Text.UTF8Encoding -ArgumentList $false
[System.IO.File]::WriteAllText($devToc, $content, $utf8)
Write-Host "TOC de desarrollo generado: $devToc"

$sourceFull = (Resolve-Path $source).Path.TrimEnd('\')

function Get-LinkTargetPath($item) {
    $value = $item.Target
    if ($value -is [array]) {
        if ($value.Count -eq 0) { return $null }
        $value = $value[0]
    }
    $value = [string]$value
    if (-not $value) { return $null }
    if (-not [System.IO.Path]::IsPathRooted($value)) {
        $value = Join-Path (Split-Path -Parent $item.FullName) $value
    }
    return [System.IO.Path]::GetFullPath($value).TrimEnd('\')
}

function Test-LinkToSource($item) {
    $resolved = Get-LinkTargetPath $item
    if (-not $resolved) { return $false }
    return [string]::Equals($resolved, $sourceFull,
                            [System.StringComparison]::OrdinalIgnoreCase)
}

# El enlace antiguo se llamaba AskForever; solo se borra si apunta a este repositorio.
# Directory.Delete sin recursiÃ³n quita solo el enlace: Remove-Item en PowerShell 5.1 puede
# actuar sobre el contenido de la carpeta enlazada (el repositorio).
if (Test-Path $oldTarget) {
    $oldItem = Get-Item $oldTarget -Force
    if ($oldItem.LinkType -in @('SymbolicLink', 'Junction') -and (Test-LinkToSource $oldItem)) {
        [System.IO.Directory]::Delete($oldTarget, $false)
        Write-Host "Enlace antiguo eliminado: $oldTarget"
    } elseif ($oldItem.LinkType -in @('SymbolicLink', 'Junction')) {
        Write-Host "Se mantiene ${oldTarget}: no apunta a este repositorio."
    } else {
        Write-Host "Existe una carpeta real en $oldTarget (instalaciÃ³n pÃºblica); no se toca."
    }
}

$alreadyLinked = $false
if (Test-Path $devTarget) {
    $devItem = Get-Item $devTarget -Force
    if ($devItem.LinkType -in @('SymbolicLink', 'Junction') -and (Test-LinkToSource $devItem)) {
        Write-Host "Ya existe el enlace de desarrollo: $devTarget -> $source"
        $alreadyLinked = $true
    } elseif ($devItem.LinkType -in @('SymbolicLink', 'Junction')) {
        [System.IO.Directory]::Delete($devTarget, $false)
        Write-Host "Enlace de desarrollo antiguo eliminado: $devTarget"
    } else {
        throw "Ya existe una carpeta real en $devTarget. MuÃ©vela o bÃ³rrala antes de crear el enlace."
    }
}

if (-not $alreadyLinked) {
    # Un enlace simbÃ³lico necesita administrador o el Modo de desarrollador; la uniÃ³n de
    # directorio (junction) no, y el juego la sigue igual.
    try {
        New-Item -ItemType SymbolicLink -Path $devTarget -Target $source -ErrorAction Stop | Out-Null
    } catch {
        New-Item -ItemType Junction -Path $devTarget -Target $source | Out-Null
    }
    Write-Host "Enlace creado: $devTarget -> $source"
}

Write-Host "Reinicia WoW por completo la primera vez (el cliente solo descubre addons al arrancar)."
