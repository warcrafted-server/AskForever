#!/usr/bin/env bash
# Genera el paquete de la versión de Linux de AskForever:
# release/askforever-<versión>-linux-x86_64.tar.gz con el programa, el addon
# público, el instalador y su suma SHA-256.
set -euo pipefail

invoke_cwd=$PWD
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(dirname -- "$script_dir")
cd "$repo_root"

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat <<'TEXT'
Uso: build-linux.sh [opciones]

Compila el companion con PyInstaller y empaqueta el programa, el addon público
y el instalador en release/askforever-<versión>-linux-x86_64.tar.gz, junto a su
archivo .sha256.

Opciones:
  --stage-only CARPETA  No compila ni prueba el programa: empaqueta la carpeta
                        indicada como programa (para pruebas).
  --out CARPETA         Carpeta de salida (por defecto release/). Con
                        --stage-only, la carpeta temporal de preparación se
                        crea dentro de ella.
  -h, --help            Muestra esta ayuda.

Variables:
  PYTHON                Intérprete con PyInstaller y Pillow (por defecto
                        build/venv-linux/bin/python si existe, si no python3).
TEXT
}

stage_only=''
out_dir="$repo_root/release"

while [ $# -gt 0 ]; do
    case $1 in
        --stage-only)
            [ $# -ge 2 ] || die 'Falta la carpeta de --stage-only'
            stage_only=$2
            shift 2
            ;;
        --stage-only=*)
            stage_only=${1#*=}
            shift
            ;;
        --out)
            [ $# -ge 2 ] || die 'Falta la carpeta de --out'
            out_dir=$2
            shift 2
            ;;
        --out=*)
            out_dir=${1#*=}
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Opción desconocida: $1 (usa --help)"
            ;;
    esac
done

resolve_path() {
    # Rutas relativas desde donde se lanzó el script, no desde la raíz.
    case $1 in
        /*) printf '%s\n' "$1" ;;
        *) printf '%s\n' "$invoke_cwd/$1" ;;
    esac
}

out_dir=$(resolve_path "$out_dir")
if [ -n "$stage_only" ]; then
    stage_only=$(resolve_path "$stage_only")
fi

version_file="$repo_root/VERSION"
toc_source="$repo_root/addon/AskForever/AskForever.toc"
[ -f "$version_file" ] || die "No existe $version_file"
[ -f "$toc_source" ] || die "No existe $toc_source"

version=$(tr -d '\r\n' < "$version_file")
[ -n "$version" ] || die "El archivo VERSION está vacío"

toc_version=''
while IFS= read -r line || [ -n "$line" ]; do
    line=${line%$'\r'}
    case $line in
        '## Version:'*)
            toc_version=${line#'## Version:'}
            toc_version=${toc_version#"${toc_version%%[![:space:]]*}"}
            toc_version=${toc_version%"${toc_version##*[![:space:]]}"}
            break
            ;;
    esac
done < "$toc_source"

if [ "$toc_version" != "$version" ]; then
    die "La versión del .toc ($toc_version) no coincide con VERSION ($version)."
fi

if [ -z "${PYTHON:-}" ]; then
    if [ -x "$repo_root/build/venv-linux/bin/python" ]; then
        PYTHON="$repo_root/build/venv-linux/bin/python"
    else
        PYTHON=python3
    fi
fi

if [ -n "$stage_only" ]; then
    dist_dir=$stage_only
    [ -d "$dist_dir" ] || die "No existe la carpeta del programa: $dist_dir"
else
    if ! "$PYTHON" -c 'import PyInstaller' >/dev/null 2>&1; then
        cat >&2 <<TEXT
Error: $PYTHON no puede importar PyInstaller.
Crea el entorno desde la raíz del repositorio con:
  python3 -m venv build/venv-linux && build/venv-linux/bin/pip install -e companion pyinstaller
Y vuelve a ejecutar este script (o indica otro intérprete con PYTHON=...).
TEXT
        exit 1
    fi

    mkdir -p "$repo_root/build/linux"
    "$PYTHON" -m PyInstaller --noconfirm --clean \
        --distpath "$repo_root/build/linux/dist" \
        --workpath "$repo_root/build/linux/work" \
        "$repo_root/companion/packaging/askforever.spec"

    dist_dir="$repo_root/build/linux/dist/AskForever"
    [ -d "$dist_dir" ] || die "PyInstaller no creó la carpeta $dist_dir"

    smoke_home=$(mktemp -d "${TMPDIR:-/tmp}/askforever-smoke.XXXXXX")
    cleanup() {
        if [ -n "${smoke_home:-}" ] && [ -d "$smoke_home" ]; then
            rm -rf -- "$smoke_home"
        fi
    }
    trap cleanup EXIT

    if ! ASKFOREVER_HOME="$smoke_home" "$dist_dir/AskForeverApp" --help >/dev/null; then
        die "El programa empaquetado falló al ejecutar --help"
    fi

    cleanup
    smoke_home=''
    trap - EXIT
fi

if [ -n "$stage_only" ]; then
    stage_root="$out_dir/stage"
else
    stage_root="$repo_root/build/linux/stage"
fi
stage_name="askforever-$version"
stage_dir="$stage_root/$stage_name"

[ -n "$stage_root" ] && [ -n "$stage_name" ] \
    || die 'No se pudo calcular la carpeta de preparación'
mkdir -p "$stage_root"
if [ -e "$stage_dir" ]; then
    rm -rf -- "$stage_dir"
fi
mkdir -p "$stage_dir/app" "$stage_dir/addon/AskForever"

# Programa compilado tal cual lo deja PyInstaller.
cp -a "$dist_dir/." "$stage_dir/app/"

install -m 755 "$repo_root/scripts/linux/install.sh" "$stage_dir/install.sh"
install -m 755 "$repo_root/scripts/linux/uninstall.sh" "$stage_dir/uninstall.sh"
cp -p "$repo_root/LICENSE" "$stage_dir/LICENSE"

# Icono del lanzador: el logo del repositorio reducido a 256x256.
logo="$repo_root/docs/img/logo.png"
[ -f "$logo" ] || die "No existe $logo"
"$PYTHON" - "$logo" "$stage_dir/app/askforever.png" <<'PY'
import sys

from PIL import Image

source, target = sys.argv[1], sys.argv[2]
with Image.open(source) as image:
    resized = image.convert('RGBA').resize((256, 256), Image.LANCZOS)
resized.save(target)
PY

# Addon público: sin dev/, sin archivos .gitkeep ni AskForeverDev.toc.
addon_source="$repo_root/addon/AskForever"
addon_target="$stage_dir/addon/AskForever"
tar -C "$addon_source" \
    --exclude='.gitkeep' \
    --exclude='dev' \
    --exclude='AskForever.toc' \
    --exclude='AskForeverDev.toc' \
    -cf - . | tar -C "$addon_target" -xf -

# El .toc público conserva el formato del repositorio pero sin las líneas dev/.
public_toc="$addon_target/AskForever.toc"
tr -d '\r' < "$toc_source" | sed '/^[[:space:]]*dev\//d' > "$public_toc"
if [ -s "$public_toc" ] && [ "$(tail -c 1 "$public_toc" | wc -l)" -eq 0 ]; then
    printf '\n' >> "$public_toc"
fi

if [ -e "$addon_target/dev" ]; then
    die "El addon empaquetado incluye dev/"
fi
if [ -e "$addon_target/AskForeverDev.toc" ]; then
    die "El addon empaquetado incluye AskForeverDev.toc"
fi

# Todo archivo del .toc público debe existir, o el addon cargaría roto.
while IFS= read -r line || [ -n "$line" ]; do
    line=${line%$'\r'}
    line=${line#"${line%%[![:space:]]*}"}
    line=${line%"${line##*[![:space:]]}"}
    [ -n "$line" ] || continue
    case $line in
        '##'*) continue ;;
    esac
    [ -f "$addon_target/$line" ] \
        || die "El paquete no incluye addon/AskForever/$line (listado en el .toc)."
done < "$public_toc"

# Si hay manifest de datos, todos los archivos de data/ deben estar dentro.
if [ -f "$addon_source/data/manifest.lua" ]; then
    while IFS= read -r -d '' data_file; do
        relative=${data_file#"$addon_source/"}
        [ -f "$addon_target/$relative" ] \
            || die "El paquete no incluye addon/AskForever/$relative."
    done < <(find "$addon_source/data" -type f ! -name '.gitkeep' -print0)
fi

# Documentos de instalación de Linux, si ya existen.
for doc in INSTALACION_LINUX.md INSTALL_LINUX.md; do
    if [ -f "$repo_root/docs/$doc" ]; then
        cp -p "$repo_root/docs/$doc" "$stage_dir/$doc"
    fi
done

mkdir -p "$out_dir"
tarball="$out_dir/$stage_name-linux-x86_64.tar.gz"
checksum="$tarball.sha256"
rm -f -- "$tarball" "$checksum"
tar -czf "$tarball" -C "$stage_root" "$stage_name"

listing=$(tar -tzf "$tarball")
if printf '%s\n' "$listing" | grep -q '/addon/AskForever/dev/'; then
    die "El tar contiene entradas de desarrollo del addon"
fi
if printf '%s\n' "$listing" | grep -qv "^$stage_name/"; then
    die "El tar contiene rutas fuera de $stage_name/"
fi

(cd "$out_dir" && sha256sum "$stage_name-linux-x86_64.tar.gz" \
    > "$stage_name-linux-x86_64.tar.gz.sha256")

printf 'Paquete: %s\n' "$tarball"
printf 'SHA-256: %s\n' "$checksum"
printf 'Preparación: %s\n' "$stage_dir"
