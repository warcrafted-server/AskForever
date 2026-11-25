#!/usr/bin/env bash
# Instalador de AskForever para WoW Forever bajo Wine/Lutris (Linux).
set -euo pipefail
shopt -s nullglob

PROGRAM_NAME='AskForeverApp'
MARKER_NAME='.askforever-install'
DESKTOP_NAME='askforever.desktop'
REQUIREMENTS_HINT='sudo pacman -S --needed gstreamer gst-plugins-base gst-plugins-good gst-plugin-pipewire xdg-desktop-portal libx11 libxext'

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat <<'TEXT'
Uso: install.sh [opciones]

Instala AskForever en la carpeta de WoW Forever y su addon en
Interface/AddOns. No hace falta ser root ni se instala nada en el sistema.

Opciones:
  --wow-dir RUTA   Carpeta del juego: la carpeta _forever_ (la que contiene
                   Wow.exe) o la carpeta "World of Warcraft" que la contiene.
                   Si no se indica, se detecta automáticamente.
  --desktop        Crea un acceso directo "AskForever App" en el menú de
                   aplicaciones del usuario.
  -h, --help       Muestra esta ayuda.
TEXT
}

cleanup() {
    if [ -n "${tmp_dir:-}" ] && [ -e "$tmp_dir" ]; then
        rm -rf -- "$tmp_dir"
    fi
    if [ -n "${backup_dir:-}" ] && [ -e "$backup_dir" ]; then
        # Interrumpido a media sustitución, el addon anterior vuelve a su sitio.
        if [ -e "${addon_target:?}" ]; then
            rm -rf -- "$backup_dir"
        else
            mv -- "$backup_dir" "$addon_target"
        fi
    fi
}
trap cleanup EXIT

toc_version() {
    # Imprime la versión de un AskForever.toc; vacío si no la encuentra.
    local toc=$1 line value
    [ -f "$toc" ] || return 0
    while IFS= read -r line || [ -n "$line" ]; do
        line=${line%$'\r'}
        case "$line" in
            '## Version:'*)
                value=${line#'## Version:'}
                value=${value#"${value%%[![:space:]]*}"}
                value=${value%"${value##*[![:space:]]}"}
                printf '%s\n' "$value"
                return 0
                ;;
        esac
    done < "$toc"
    return 0
}

version_is_newer() {
    # True si $1 es una versión mayor que $2, con el mismo orden que sort -V.
    local candidate=$1 reference=$2 greatest
    [ "$candidate" != "$reference" ] || return 1
    greatest=$(printf '%s\n%s\n' "${candidate//-/\~}" "${reference//-/\~}" \
        | sort -V | tail -n 1)
    [ "$greatest" = "${candidate//-/\~}" ]
}

has_wow_exe() {
    local folder=$1
    [ -d "$folder" ] || return 1
    [ -n "$(find "$folder" -maxdepth 1 -iname 'wow.exe' -print -quit 2>/dev/null)" ]
}

resolve_wow_dir() {
    # Acepta la carpeta _forever_ o la carpeta "World of Warcraft" que la contiene.
    local given=$1 candidate
    [ -d "$given" ] || return 1
    given=$(cd -- "$given" && pwd -P)
    if has_wow_exe "$given"; then
        printf '%s\n' "$given"
        return 0
    fi
    if candidate=$(find_child_ci "$given" '_forever_') && has_wow_exe "$candidate"; then
        printf '%s\n' "$candidate"
        return 0
    fi
    return 1
}

find_child_ci() {
    # Busca una subcarpeta sin distinguir mayúsculas: $1 padre, $2 nombre.
    local parent=$1 wanted=$2 entry base
    for entry in "$parent"/*; do
        [ -d "$entry" ] || continue
        base=${entry##*/}
        if [ "${base,,}" = "${wanted,,}" ]; then
            printf '%s\n' "$entry"
            return 0
        fi
    done
    return 1
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

escape_exec() {
    # Escapa un valor para la clave Exec de un archivo .desktop.
    local value=$1
    value=${value//\\/\\\\}
    value=${value//\"/\\\"}
    value=${value//\`/\\\`}
    value=${value//\$/\\\$}
    value=${value//\\/\\\\}
    value=${value//\%/%%}
    printf '%s' "$value"
}

copy_addon() {
    # Copia el addon a una carpeta temporal hermana y luego sustituye la antigua.
    local source=$addon_src target=$addon_target
    tmp_dir=''
    backup_dir=''
    tmp_dir=$(mktemp -d -- "$addons_dir/.askforever-nuevo.XXXXXX")
    if ! cp -R -- "$source/." "$tmp_dir/"; then
        die "No se pudo copiar el addon a $tmp_dir."
    fi
    # mktemp la crea solo para el usuario.
    chmod 0755 -- "$tmp_dir"
    if [ -e "$target" ] || [ -L "$target" ]; then
        backup_dir=$(mktemp -d -- "$addons_dir/.askforever-anterior.XXXXXX")
        rmdir -- "$backup_dir"
        mv -- "$target" "$backup_dir"
    fi
    if ! mv -- "$tmp_dir" "$target"; then
        if [ -n "$backup_dir" ]; then
            mv -- "$backup_dir" "$target"
        fi
        die "No se pudo colocar el addon en $target."
    fi
    tmp_dir=''
    if [ -n "$backup_dir" ]; then
        rm -rf -- "$backup_dir"
        backup_dir=''
    fi
    printf 'Addon instalado en %s\n' "$target"
}

wow_arg=''
wow_given=0
want_desktop=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --wow-dir)
            [ "$#" -ge 2 ] || die 'Falta la ruta después de --wow-dir.'
            wow_arg=$2
            wow_given=1
            shift 2
            ;;
        --wow-dir=*)
            wow_arg=${1#--wow-dir=}
            wow_given=1
            shift
            ;;
        --desktop)
            want_desktop=1
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

if [ "$(id -u)" -eq 0 ]; then
    die 'No ejecutes el instalador como root: instala en la carpeta del juego del usuario, no en el sistema.'
fi

src_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
app_src="$src_dir/app/$PROGRAM_NAME"
addon_src="$src_dir/addon/AskForever"
[ -f "$app_src" ] || die "No se encontró el programa en $app_src. Ejecuta install.sh desde la carpeta extraída del tar.gz."
[ -d "$addon_src" ] || die "No se encontró el addon en $addon_src. Ejecuta install.sh desde la carpeta extraída del tar.gz."
[ -f "$src_dir/uninstall.sh" ] || die "No se encontró uninstall.sh en $src_dir."

bundle_version=$(toc_version "$addon_src/AskForever.toc")

if [ "$wow_given" -eq 1 ]; then
    [ -n "$wow_arg" ] || die 'La ruta de --wow-dir está vacía.'
    game=$(resolve_wow_dir "$wow_arg") || die "La ruta indicada no contiene Wow.exe: $wow_arg. Indica la carpeta _forever_ o la carpeta \"World of Warcraft\" que la contiene."
else
    detected=''
    if detected=$("$app_src" find-wow 2>/dev/null); then
        :
    else
        detected=''
    fi
    found=()
    while IFS= read -r line; do
        line=${line%$'\r'}
        if [ -n "$line" ]; then
            found+=("$line")
        fi
    done <<< "$detected"
    if [ "${#found[@]}" -eq 0 ]; then
        die 'No se encontró ninguna carpeta de WoW Forever. Repite con --wow-dir RUTA (la carpeta _forever_ o la carpeta "World of Warcraft" que la contiene).'
    fi
    if [ "${#found[@]}" -gt 1 ]; then
        printf 'Se encontraron varias carpetas de WoW Forever:\n' >&2
        for line in "${found[@]}"; do
            printf '  - %s\n' "$line" >&2
        done
        die 'Repite con --wow-dir RUTA para elegir una de ellas.'
    fi
    game=$(resolve_wow_dir "${found[0]}") || die "La carpeta detectada no contiene Wow.exe: ${found[0]}"
fi

has_wow_exe "$game" || die "No se encontró Wow.exe en $game."
target="$game/AskForever"
target_real=$(readlink -f -- "$target" 2>/dev/null || printf '%s\n' "$target")

if [ -L "$target" ]; then
    die "La carpeta $target es un enlace simbólico; no se instala encima."
fi
if [ -e "$target" ] && [ ! -d "$target" ]; then
    die "$target existe y no es una carpeta; no se toca."
fi
if folder_in_use "$target_real"; then
    die "Hay un proceso ejecutándose desde $target. Cierra AskForever y vuelve a intentarlo."
fi
if [ -d "$target" ] && [ ! -e "$target/$MARKER_NAME" ]; then
    shopt -s dotglob
    entries=("$target"/*)
    shopt -u dotglob
    if [ "${#entries[@]}" -gt 0 ]; then
        die "$target ya existe, no está vacía y no parece una instalación de AskForever. No se toca nada."
    fi
fi

mkdir -p -- "$target"
install -m 0755 -- "$app_src" "$target/$PROGRAM_NAME"
if [ -d "$src_dir/app/_internal" ]; then
    rm -rf -- "$target/_internal"
    cp -R -- "$src_dir/app/_internal" "$target/_internal"
fi
rm -f -- "$target/askforever.png"
if [ -f "$src_dir/app/askforever.png" ]; then
    cp -- "$src_dir/app/askforever.png" "$target/askforever.png"
fi
cp -- "$src_dir/uninstall.sh" "$target/uninstall.sh"
chmod 0755 -- "$target/$PROGRAM_NAME" "$target/uninstall.sh"
printf 'version=%s\n' "${bundle_version:-desconocida}" > "$target/$MARKER_NAME"
printf 'Programa instalado en %s\n' "$target"

interface_dir=''
if ! interface_dir=$(find_child_ci "$game" 'interface'); then
    interface_dir="$game/Interface"
    mkdir -p -- "$interface_dir"
fi
addons_dir=''
if ! addons_dir=$(find_child_ci "$interface_dir" 'addons'); then
    addons_dir="$interface_dir/AddOns"
    mkdir -p -- "$addons_dir"
fi

addon_target="$addons_dir/AskForever"
if [ -L "$addon_target" ]; then
    printf 'Aviso: %s es un enlace simbólico; se deja tal cual.\n' "$addon_target"
else
    installed_version=$(toc_version "$addon_target/AskForever.toc")
    if [ -n "$installed_version" ] && [ -n "$bundle_version" ] \
        && version_is_newer "$installed_version" "$bundle_version"; then
        printf 'Se conserva el addon instalado (%s), que es más nuevo que el incluido (%s).\n' \
            "$installed_version" "$bundle_version"
    else
        copy_addon
    fi
fi

if [ "$want_desktop" -eq 1 ]; then
    if [ -n "${XDG_DATA_HOME:-}" ]; then
        data_home=$XDG_DATA_HOME
    elif [ -n "${HOME:-}" ]; then
        data_home="$HOME/.local/share"
    else
        die 'No se puede crear el acceso directo: define HOME o XDG_DATA_HOME.'
    fi
    mkdir -p -- "$data_home/applications"
    desktop_file="$data_home/applications/$DESKTOP_NAME"
    exec_path="$target/$PROGRAM_NAME"
    escaped_exec=$(escape_exec "$exec_path")
    {
        printf '[Desktop Entry]\n'
        printf 'Type=Application\n'
        printf 'Name=AskForever App\n'
        printf 'Comment=Asistente de IA para WoW Forever\n'
        printf 'Exec="%s" app\n' "$escaped_exec"
        printf 'Terminal=false\n'
        printf 'Categories=Game;\n'
        if [ -f "$target/askforever.png" ]; then
            printf 'Icon=%s\n' "$target/askforever.png"
        fi
        printf 'X-AskForever-Dir=%s\n' "$target"
    } > "$desktop_file"
    chmod 0644 -- "$desktop_file"
    printf '%s\n' "$desktop_file" > "$target/.desktop-path"
    printf 'Acceso directo creado en %s\n' "$desktop_file"
fi

missing=()
if ! command -v gst-launch-1.0 >/dev/null 2>&1; then
    missing+=('gst-launch-1.0')
fi
if command -v gst-inspect-1.0 >/dev/null 2>&1; then
    if ! gst-inspect-1.0 pipewiresrc >/dev/null 2>&1; then
        missing+=('gst-inspect-1.0 pipewiresrc')
    fi
    if ! gst-inspect-1.0 videocrop >/dev/null 2>&1; then
        missing+=('gst-inspect-1.0 videocrop')
    fi
else
    missing+=('gst-inspect-1.0')
fi
if [ "${#missing[@]}" -gt 0 ]; then
    printf 'Aviso: faltan componentes del sistema para la captura de pantalla: %s\n' \
        "$(printf '%s, ' "${missing[@]}" | sed 's/, $//')"
    printf 'Puedes instalarlos con:\n  %s\n' "$REQUIREMENTS_HINT"
fi

printf '\nAskForever se ha instalado en %s\n' "$target"
printf 'Para abrir la aplicación: %s app\n' "$target/$PROGRAM_NAME"
if [ "$want_desktop" -eq 1 ]; then
    printf 'También tienes el acceso directo "AskForever App" en el menú de aplicaciones.\n'
fi
printf 'Para desinstalar: %s\n' "$target/uninstall.sh"
printf 'Recuerda: WoW debe ejecutarse en pantalla completa sin bordes (borderless) para que el overlay funcione.\n'
