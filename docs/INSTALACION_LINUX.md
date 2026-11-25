# Guía de instalación de AskForever para Linux (ES)

**[English version](INSTALL_LINUX.md)**

Esta guía explica cómo instalar y usar AskForever en Linux. La primera configuración tarda unos **10 minutos**.

AskForever tiene dos partes:

- El **addon**: la ventana de AskForever dentro de World of Warcraft.
- **AskForever App**: una app de Linux que conecta el addon con la IA y muestra las respuestas sobre el juego.

Si usas Windows, consulta la [guía de instalación para Windows](https://github.com/warcrafted-server/AskForever/blob/main/docs/GUIA_INSTALACION.md).

## Antes de empezar

Necesitas:

- Linux **x86_64**. La 0.5.0-beta.1 es la primera versión para Linux y solo se ha probado en **Arch Linux y derivadas, con KDE Plasma en Wayland** y el juego en Lutris. En otros escritorios y distribuciones no está probada.
- El **portal del escritorio** y un **llavero Secret Service** (KWallet o GNOME Keyring), además de los paquetes del paso 1.
- World of Warcraft: **WoW Forever** instalado y funcionando con Wine o Proton (Lutris o Steam), en modo **ventana sin bordes** a pantalla completa.
- Una **cuenta de Google**, gratuita, para crear la clave de Gemini.

## 1. Instalar los paquetes necesarios

En Arch Linux y derivadas, instala los paquetes necesarios para la captura de pantalla y el overlay:

```
sudo pacman -S --needed gstreamer gst-plugins-base gst-plugins-good gst-plugin-pipewire xdg-desktop-portal libx11 libxext
```

Además necesitas el portal de tu escritorio (en KDE, el paquete `xdg-desktop-portal-kde`) y un llavero Secret Service, como KWallet o GNOME Keyring. AskForever App guarda la clave de IA en ese llavero.

## 2. Descargar e instalar AskForever

El paquete de Linux instala a la vez el addon y AskForever App.

1. En la [página de la última versión](https://github.com/warcrafted-server/AskForever/releases/latest), descarga **`askforever-<versión>-linux-x86_64.tar.gz`** y su archivo **`.sha256`**.
2. Comprueba la descarga en la carpeta donde están los dos archivos:

   ```
   sha256sum -c askforever-<versión>-linux-x86_64.tar.gz.sha256
   ```

3. Extrae el paquete:

   ```
   tar -xzf askforever-<versión>-linux-x86_64.tar.gz
   ```

4. Entra en la carpeta `askforever-<versión>` y ejecuta el instalador. **No hace falta root**:

   ```
   ./install.sh --desktop
   ```

   Opciones de `install.sh`:

   - `--wow-dir RUTA`: la carpeta `_forever_` del juego (o la carpeta `World of Warcraft`).
   - `--desktop`: añade un acceso directo **AskForever App** al menú de aplicaciones. Es lo único que se crea fuera de la carpeta del juego.
   - `--help`: muestra la ayuda.

   Sin `--wow-dir`, el instalador busca el juego en los prefijos habituales de Lutris, Wine, Steam y Bottles. Si encuentra varios o ninguno, te pide la carpeta.

5. Cuando termine, abre **AskForever App** desde el menú de aplicaciones.

El instalador instala la app en `<_forever_>/AskForever/` y el addon en `<_forever_>/Interface/AddOns/AskForever`. En esta guía, `<_forever_>` es la carpeta `_forever_` de tu instalación del juego. Si el addon que ya tienes instalado es más nuevo, se conserva. El addon también se puede instalar y actualizar desde CurseForge.

Si prefieres no usar el acceso directo, abre la app con:

```
<_forever_>/AskForever/AskForeverApp app
```

## 3. Primer arranque: configurar la IA y la pantalla

1. La primera vez se abre el diálogo **Configurar IA** para Google Gemini. Sigue la [guía de la clave de Gemini](https://github.com/warcrafted-server/AskForever/blob/main/docs/CLAVE_GEMINI.md) para conseguir una clave gratuita, introdúcela en el diálogo y pulsa **Probar y guardar**. La app prueba la clave antes de guardarla en el **llavero del escritorio** (servicio `AskForever`). La clave nunca se guarda en un archivo.
2. Con WoW abierto, el escritorio pide **compartir pantalla**: elige el monitor donde está el juego. La elección se recuerda en `AskForever/data/portal-token`. Para elegir otro monitor, borra ese archivo y vuelve a abrir la app.
3. AskForever App solo captura la pantalla mientras el juego está abierto.

## 4. Jugar

1. Mantén **AskForever App en marcha** mientras juegas; el addon la necesita para responder preguntas.
2. Abre WoW Forever e inicia sesión.
3. En el juego, escribe `/af` (o `/askforever`) en el chat del juego y pulsa Enter, o haz clic en el botón **AskForever** del minimapa. Se abre la ventana del chat de AskForever.
4. Escribe tu pregunta en esa ventana y pulsa Enter. Por ejemplo: *¿Por dónde voy a Baldíos?*
5. La respuesta aparece en la conversación de la ventana del addon. Desplázate por la conversación con la rueda del ratón encima o con sus botones de flecha, mueve la ventana y cámbiale el tamaño desde la esquina inferior derecha. El panel de la respuesta no intercepta los clics: lo atraviesan.

### Ventana y bandeja del sistema de AskForever App

Al cerrar la ventana de la app, sigue en marcha en la bandeja del sistema. Haz clic en el icono de la bandeja para volver a abrirla; el menú del icono tiene **Abrir** y **Salir**.

## Actualizar

- **AskForever App** solo avisa de una versión nueva con su enlace; no descarga ni ejecuta nada. Para actualizar, cierra la app, extrae el paquete nuevo y ejecuta `./install.sh` otra vez. Se conservan la clave y los datos.
- **Addon, datos del juego y fichas:** actualiza el addon **AskForever** en CurseForge, o instala el nuevo paquete de Linux como se explica arriba.

## Desinstalar

Con la app cerrada, ejecuta:

```
<_forever_>/AskForever/uninstall.sh
```

Añade `--yes` para no tener que confirmar. Se eliminan la clave, los datos, los registros, el addon, la carpeta de la app y el acceso directo.

## Limitaciones conocidas

- En GNOME, el icono de la bandeja necesita una extensión AppIndicator. No está probado.
- Con Wine o Proton en Wayland nativo, el panel no se oculta al cambiar a otra ventana.
- No se han probado: GNOME ni otros escritorios o distribuciones, WoW bajo XWayland dentro del juego, sesiones X11, ni varios monitores con el juego fuera del monitor izquierdo.

## Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| No aparece el diálogo de compartir pantalla en KDE tras actualizar Qt sin cerrar sesión | Ejecuta `systemctl --user restart plasma-xdg-desktop-portal-kde.service xdg-desktop-portal.service`, o reinicia el equipo, y vuelve a abrir la app. |
| El diálogo de compartir pantalla no se ve | Búscalo con Alt+Tab o en el otro monitor. Caduca a los dos minutos y se repite. |
| El icono no aparece en la bandeja (GNOME) | Instala una extensión AppIndicator. No está probado. |

### Registros

Si algo falla, revisa:

- `<_forever_>/AskForever/logs/app.log`: el registro de la app.
- `<_forever_>/AskForever/companion.log`: el registro de la captura de pantalla. Anota su arranque, el primer fotograma y los errores de GStreamer.

## Seguridad y transparencia

- **Pantalla:** el portal del escritorio comparte el monitor elegido con un proceso `gst-launch-1.0` local, que recorta la esquina superior izquierda de 512 × 32 píxeles. La app solo recibe ese recorte, no guarda imágenes y no captura con el juego cerrado. El permiso concedido al portal abarca el monitor completo.
- **Juego:** detecta WoW leyendo la lista de procesos de `/proc` (línea de órdenes, entorno y archivos mapeados del proceso `Wow.exe`, solo para saber su carpeta). No lee la memoria del juego, no inyecta nada ni simula teclado o ratón.
- **Archivos:** `<_forever_>/AskForever/` contiene el programa, `data/`, `logs/` y los archivos `companion.log`, `data/portal-token` y `data/portal-geometry.json`. La carpeta `data/` del addon es de solo lectura. La clave está en el llavero y, si usas `--desktop`, se añade `~/.local/share/applications/askforever.desktop`.
- **Red:** las mismas conexiones que en Windows (el proveedor de IA elegido, warcraft.wiki.gg y GitHub). En Linux, de GitHub solo lee la lista de versiones y descarga la base de datos del juego.

El [informe de seguridad y transparencia](https://github.com/warcrafted-server/AskForever/blob/main/docs/SEGURIDAD_TRANSPARENCIA.md) explica qué hace AskForever App y qué no hace nunca.

## Compilar desde el código (opcional)

Si quieres compilar el paquete tú mismo, desde la raíz del repositorio:

```
python3 -m venv build/venv-linux && build/venv-linux/bin/pip install -e companion pyinstaller && bash scripts/build-linux.sh
```

El paquete se genera en `release/`. Necesitas **Python 3.12 o posterior con tkinter**; en Arch Linux, el paquete `tk`.

El paquete oficial de Linux se compila en GitHub Actions desde la 0.5.0-beta.1, con SHA-256 y prueba de procedencia que se puede comprobar con `gh attestation verify`. No hay análisis de VirusTotal publicado para Linux.
