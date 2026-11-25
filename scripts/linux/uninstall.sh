#!/usr/bin/env bash
# Desinstalador de AskForever para WoW Forever bajo Wine/Lutris (Linux).
# Este archivo se instala dentro de la carpeta del juego:
#   <juego>/AskForever/uninstall.sh
set -euo pipefail
shopt -s nullglob

PROGRAM_NAME='AskForeverApp'
MARKER_NAME='.askforever-install'
DESKTOP_NAME='askforever.desktop'

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat <<'TEXT'
Uso: uninstall.sh [opciones]

Desinstala AskForever: borra sus claves de API, sus datos, su addon y su
carpeta <juego>/AskForever, y el acceso directo si se creó con --desktop.
No toca nada más. Ejecuta el uninstall.sh que está dentro de la carpeta
<juego>/AskForever del juego; el de la carpeta extraída del tar.gz no sirve.

Opciones:
  --yes, -y     No pide confirmación.
  --force, -f   Borra la carpeta aunque el programa no pueda desinstalar sus
                datos o falte.
  -h, --help    Muestra esta ayuda.
TEXT
}

folder_in_use() {
    # True si algún proceso en ejecución sale de esa carpeta.
    local wanted=$1 link exe
    for link in /proc/[0-9]*/exe; do
        exe=$(readlink -f -- "$link" 2>/dev/null) || continue
        case "$exe" in
            "$wanted"/*) return 0 ;;
        esac
    done
    return 1
}

parent_looks_like_game() {
    local parent=$1 entry base
    for entry in "$parent"/*; do
        [ -d "$entry" ] || continue
        base=${entry##*/}
        if [ "${base,,}" = 'interface' ]; then
            return 0
        fi
    done
    if [ -n "$(find "$parent" -maxdepth 1 -iname 'wow.exe' -print -quit 2>/dev/null)" ]; then
        return 0
    fi
    return 1
}

assume_yes=0
force=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --yes|-y)
            assume_yes=1
            shift
            ;;
        --force|-f)
            force=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Opción desconocida: $1 (prueba --help)."
            ;;
    esac
done

script_path=$(readlink -f -- "${BASH_SOURCE[0]}") \
    || die 'No se pudo resolver la ruta de este desinstalador.'
dir=$(dirname -- "$script_path")
name=${dir##*/}
parent=$(dirname -- "$dir")

if [ "$name" != 'AskForever' ] || [ ! -f "$dir/$MARKER_NAME" ] \
    || ! parent_looks_like_game "$parent"; then
    die "Esto no es una instalación de AskForever dentro de una carpeta de juego ($dir). Ejecuta el desinstalador que está en <juego>/AskForever/uninstall.sh."
fi

if folder_in_use "$dir"; then
    die "Hay un proceso ejecutándose desde $dir. Cierra AskForever y vuelve a intentarlo."
fi

if [ "$assume_yes" -eq 0 ]; then
    if [ ! -t 0 ]; then
        die 'Sin confirmación: vuelve a ejecutarlo desde un terminal o añade --yes.'
    fi
    printf 'Se borrarán AskForever (%s), sus datos, su addon y su acceso directo.\n' "$dir"
    answer=''
    read -r -p '¿Continuar? [s/N]: ' answer || answer=''
    case "${answer,,}" in
        s|si|sí|y|yes) ;;
        *)
            printf 'Desinstalación cancelada.\n'
            exit 1
            ;;
    esac
fi

program="$dir/$PROGRAM_NAME"
program_ok=0
if [ -x "$program" ]; then
    if env -u ASKFOREVER_HOME "$program" uninstall --yes --addon; then
        program_ok=1
    fi
else
    printf 'Aviso: no se encontró %s.\n' "$program" >&2
fi
if [ "$program_ok" -eq 0 ]; then
    if [ "$force" -eq 0 ]; then
        die 'El programa no pudo borrar sus claves, datos o addon; se conserva la carpeta. Usa --force para borrarla de todos modos.'
    fi
    printf 'Aviso: se continúa por --force.\n' >&2
fi

desktop_marker="$dir/.desktop-path"
if [ -f "$desktop_marker" ]; then
    desktop_file=''
    IFS= read -r desktop_file < "$desktop_marker" || desktop_file=''
    desktop_file=${desktop_file%$'\r'}
    if [ -n "$desktop_file" ] && [ "${desktop_file##*/}" = "$DESKTOP_NAME" ] \
        && [ -f "$desktop_file" ] && [ ! -L "$desktop_file" ] \
        && grep -qxF -- "X-AskForever-Dir=$dir" "$desktop_file" \
        && grep -q '^Exec=.*AskForeverApp' "$desktop_file"; then
        rm -f -- "$desktop_file"
        printf 'Acceso directo eliminado: %s\n' "$desktop_file"
    else
        printf 'Aviso: el acceso directo %s no es de esta instalación; no se toca.\n' "$desktop_file"
    fi
fi

cd /
rm -rf -- "${dir:?}"
printf 'AskForever desinstalado.\n'
