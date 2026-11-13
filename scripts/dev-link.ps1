# AskForever — enlace simbólico de desarrollo
# Uso (PowerShell como administrador, o con el Modo de desarrollador de Windows activado):
#   .\scripts\dev-link.ps1
#   .\scripts\dev-link.ps1 -AddOnsPath "D:\Juegos\World of Warcraft\_forever_\Interface\AddOns"

param(
    [string]$AddOnsPath = "C:\Wow\World of Warcraft\_forever_\Interface\AddOns"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$source   = Join-Path $repoRoot "addon\AskForever"
$target   = Join-Path $AddOnsPath "AskForever"

if (-not (Test-Path $source))     { throw "No existe la carpeta del addon: $source" }
if (-not (Test-Path $AddOnsPath)) { throw "No existe la carpeta AddOns: $AddOnsPath" }

if (Test-Path $target) {
    $item = Get-Item $target -Force
    if ($item.LinkType -eq "SymbolicLink") {
        Write-Host "Ya existe el enlace -> $($item.Target)"
        exit 0
    }
    throw "Ya existe una carpeta real en $target. Muévela o bórrala antes de crear el enlace."
}

New-Item -ItemType SymbolicLink -Path $target -Target $source | Out-Null
Write-Host "Enlace creado: $target -> $source"
Write-Host "Reinicia WoW por completo la primera vez (el cliente solo descubre addons al arrancar)."
