# Guía de instalación de AskForever (ES)

**[English version](INSTALL_GUIDE.md)**

> 🚧 Guía de la **v0.1.0-beta**, que funciona en el juego pero aún no está publicada (la página de CurseForge todavía no existe, así que por ahora el addon se instala desde el repositorio). Esta guía se actualiza con cada versión. Si algún paso no coincide con lo que ves, revisa la última versión en GitHub.

Tiempo estimado: **2 minutos**, una sola vez.

## Qué hace la v0.1.0

La v0.1.0 solo contiene el **addon**. Recoge el contexto de tu personaje (nivel, raza, clase, facción, zona, coordenadas, misiones activas) y construye un prompt listo para copiar y pegar en cualquier chat de IA (Gemini, ChatGPT, Claude…). Recibir la respuesta dentro del juego requiere el **companion**, que llegará en versiones posteriores (consulta la [hoja de ruta](../ROADMAP.md)).

## Requisitos

- WoW Forever instalado.
- Nada más para la v0.1.0.

## 1. Instalar el addon

### Opción A: aplicación de CurseForge (recomendada)
1. Abre la app de **CurseForge** → **World of Warcraft**.
2. Comprueba que está seleccionada la instalación **Forever**. Si no aparece, usa *Scan for games* o añade a mano la carpeta `World of Warcraft\_forever_`.
3. Busca **AskForever** y pulsa **Install**.

### Opción B: manual
1. Descarga el `.zip` desde la página de AskForever en CurseForge (pestaña **Files**).
2. Descomprímelo y copia la carpeta `AskForever` en `World of Warcraft\_forever_\Interface\AddOns\`.
3. Debe quedar así: `...\AddOns\AskForever\AskForever.toc`

### Hasta que esté en CurseForge: desde GitHub
1. En la [página del repositorio](https://github.com/warcrafted-server/AskForever) pulsa **Code → Download ZIP** y descomprímelo.
2. Copia solo la carpeta `addon\AskForever` (no todo el repositorio) en `World of Warcraft\_forever_\Interface\AddOns\`.
3. Debe quedar así: `...\AddOns\AskForever\AskForever.toc`

## 2. Iniciar el juego

Si el juego estaba abierto, **ciérralo del todo y vuelve a abrirlo**: `/reload` no detecta addons nuevos. En la selección de personaje, pulsa **AddOns** y comprueba que **AskForever** está activado.

## 3. Haz tu primera pregunta

1. Entra con tu personaje.
2. Abre AskForever con `/af` (o `/askforever`), o con el atajo que configures en *Opciones → Atajos → AddOns → AskForever*.
3. La ventana muestra un resumen de tu personaje (nivel, raza, clase, zona). Escribe tu pregunta, por ejemplo: *¿por dónde voy a Baldíos?*, y pulsa Enter. La pregunta aparece en el historial con el aviso «Prompt listo».
4. Pulsa **Copiar prompt**. Aparece una caja con el prompt ya seleccionado: pulsa `Ctrl+C`.
5. Pégalo en el chat de IA que prefieras. No hace falta decir tu nivel, facción ni dónde estás: el prompt ya los incluye.

El botón del minimapa abre y cierra la ventana. Arrástralo para moverlo; `/af minimap` lo muestra u oculta.

## Companion (versión para desarrolladores, v0.2)

La versión 0.2 añade el **companion**, un programa en Python que lee tu pregunta de la pantalla, consulta a Google Gemini y muestra la respuesta sobre el juego. Todavía no va en el paquete de CurseForge (el instalador está previsto para la 0.4.0): por ahora se ejecuta desde el repositorio.

**Requisitos:** Windows 10 u 11, Python 3.12, el juego en modo **Ventana** o **Ventana (sin bordes)** (probado a 1920x1080; en pantalla completa exclusiva no se puede capturar), el addon de la misma versión y una clave de Gemini ([guía](CLAVE_GEMINI.md)).

En **PowerShell**, desde la carpeta del proyecto:

1. Crea el entorno e instala las dependencias (una sola vez):

   ```powershell
   cd companion
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install mss pillow keyring openai
   ```

2. Guarda tu clave (una sola vez): sigue el paso 2 de la [guía de la clave de Gemini](CLAVE_GEMINI.md).
3. Comprueba la clave: `.venv\Scripts\python.exe -m askforever test-key`. Debe mostrar el modelo, el tiempo y `Respuesta: OK`.
4. Opcional, para ver el overlay sin el juego: `.venv\Scripts\python.exe -m askforever overlay-demo`.
5. Arráncalo con el juego abierto: `.venv\Scripts\python.exe -m askforever run`. En el juego, abre `/af`, escribe tu pregunta y pulsa Enter: una tira de colores se ve unos 2 segundos arriba a la izquierda y después aparecen «Pensando…» y la respuesta a la derecha de la pantalla. Páralo con `Ctrl+C`.

El overlay deja pasar los clics y nunca roba el foco. Si algo falla, `/af selftest` y `/af pattern` en el juego ayudan a diagnosticar el transporte.

**Límites conocidos:** sin memoria entre preguntas, sin datos de profesiones, talentos ni inventario y sin datos de juego verificados, así que las respuestas pueden ser erróneas. Están previstos para las próximas versiones.

## Solución de problemas

| Problema | Solución |
|---|---|
| `/af` no hace nada | AskForever no está activado o no reiniciaste el juego tras instalarlo. Revisa el paso 2. |
| Sale un error al entrar | Instala **BugSack** y **BugGrabber**, repite el error y abre una [incidencia en GitHub](https://github.com/warcrafted-server/AskForever/issues) con el texto. |
| El prompt muestra una zona equivocada o no hay misiones | Vuelve a abrir la ventana tras cambiar de zona; si persiste, avísanos. |
| La ventana se ha perdido fuera de la pantalla | Ejecuta `/af reset` para restaurar su posición (disponible desde la v0.1.0). |

## Desinstalar

Desinstálalo desde la app de CurseForge o borra `Interface\AddOns\AskForever`. Tus ajustes están en `WTF\Account\<cuenta>\SavedVariables\AskForever.lua` (borrarlos es opcional).

## Preguntas frecuentes

**¿Es gratis?** Sí.

**¿Me pueden banear?** AskForever no simula teclas, no lee la memoria del juego ni automatiza acciones: solo muestra información con la API oficial de addons. Aun así, Blizzard no se ha pronunciado sobre este tipo de herramientas, así que no se puede garantizar nada. Úsalo bajo tu responsabilidad.

**¿Qué datos maneja?** Tu pregunta y el contexto de tu personaje. En la v0.1.0 no se envía nada a ningún sitio: tú decides qué pegas y dónde.

**¿Funciona en Mac o Linux?** El addon funciona donde funcione el juego. El companion (versiones futuras) será solo para Windows al principio.
