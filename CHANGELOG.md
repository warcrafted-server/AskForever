# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/). Versioning: [SemVer](https://semver.org/). English first, then Spanish / Inglés primero, después español.

## [Unreleased]

### English
- Fixed: since 0.3.0-beta.3 the answer window appeared in the top-left corner instead of on the right, over the pixel strip, so a new question asked while it was visible could be lost.
- Added: the VirusTotal report of the installer is linked from the README badge and the security and transparency page, which also explains the single detection (SecureAge, generic label) of 0.3.0-beta.3.
- Added: the development copy loads as AskForever (dev) next to the public addon, with a warning when both are enabled.
- Added: the addon sends the position of its conversation panel and tells the companion when its window opens, closes or moves (for the in-window chat).
- Added: chat inside the addon window: the companion draws the whole conversation over the addon's conversation panel and follows the window when it opens, closes or moves; without that information it keeps the classic answer window.

### Español
- Corregido: desde la 0.3.0-beta.3 la ventana de respuesta aparecía en la esquina superior izquierda en vez de a la derecha, encima de la tira de píxeles, y una pregunta nueva hecha mientras se veía podía perderse.
- Añadido: el informe de VirusTotal del instalador se enlaza desde la insignia del README y la página de seguridad y transparencia, que también explica la única detección (SecureAge, etiqueta genérica) de la 0.3.0-beta.3.
- Añadido: la copia de desarrollo se carga como AskForever (desarrollo) junto al addon público, con un aviso cuando ambos están activados.
- Añadido: el addon envía la posición de su panel de conversación y avisa al companion cuando su ventana se abre, se cierra o se mueve (para el chat dentro de la ventana).
- Añadido: chat dentro de la ventana del addon: el companion dibuja toda la conversación sobre el panel de conversación del addon y sigue a la ventana al abrirla, cerrarla o moverla; sin esa información mantiene la ventana de respuesta clásica.

## [0.3.0-beta.3] - 2026-11-15

Quest questions now include where their objective items come from. / Las preguntas de misión ahora incluyen de dónde salen sus objetos objetivo.

### English
- Fixed: questions about a quest now include where its objective items come from (which NPC drops them, with zone, coordinates and drop rate; vendors; quest rewards).
- Fixed: quest questions also include the world objects (chests, crates, plants...) that give the objective items and where the creatures of kill quests are, with zone and coordinates.
- Added: the addon sends the ID of each active quest; same-name quests are resolved with your quest log; questions that refer to an active quest without its name ('who drops the book?', 'where are those kobolds?') use that quest's data when the match is clear.
- Fixed: the answer overlay no longer flashes or takes the focus from the game when it starts or restarts, and it hides while the game is minimized or in the background.

### Español
- Corregido: las preguntas sobre una misión ahora incluyen de dónde salen sus objetos objetivo (qué PNJ los suelta, con zona, coordenadas y probabilidad; vendedores; recompensas de misión).
- Corregido: las preguntas de misión también incluyen los objetos del mundo (cofres, cajas, plantas...) que dan los objetos objetivo y dónde están las criaturas de las misiones de matar, con zona y coordenadas.
- Añadido: el addon envía el ID de cada misión activa; las misiones con el mismo nombre se resuelven con tu registro de misiones; las preguntas que se refieren a una misión activa sin nombrarla ('¿quién suelta el libro?', '¿dónde están esos kobolds?') usan sus datos cuando la coincidencia es clara.
- Corregido: la ventana de respuesta ya no parpadea ni roba el foco al juego al iniciarse o reiniciarse, y se oculta mientras el juego está minimizado o en segundo plano.

## [0.3.0-beta.2] - 2026-11-15

Welcome and help window with the setup steps and links. / Ventana de bienvenida y ayuda con los pasos de instalación y los enlaces.

### English
- Added: welcome window on first login that explains the companion, the free Gemini key and the setup links, with Copy buttons.
- Added: help window from the '?' button in the main window and from '/af help'.
- Added: the addon download includes README.txt and the installation guides and the security and data transparency report (docs/).

### Español
- Añadido: ventana de bienvenida en el primer inicio de sesión que explica el companion, la clave gratuita de Gemini y los enlaces de instalación, con botones Copiar.
- Añadido: ventana de ayuda desde el botón '?' de la ventana principal y desde '/af help'.
- Añadido: la descarga del addon incluye README.txt y las guías de instalación y el informe de seguridad y transparencia de datos (docs/).

## [0.3.0-beta.1] - 2026-11-14

First functional public beta: the addon on CurseForge and the companion installer on GitHub Releases. / Primera beta pública funcional: el addon en CurseForge y el instalador del companion en GitHub Releases.

### English
- Added: the companion supports several OpenAI-compatible cloud providers (Gemini, Groq, Mistral, Cerebras, OpenRouter), one key and one model per provider, with `providers`, `list-models` and `--provider` / `--model` options.
- Added: verified game data from a local wowdata database (read-only): quests (giver, turn-in, objectives), NPC locations, class trainer spells and trainers, dungeon entrances, flight points, talent trees and item sources are detected in the question and passed to the AI, which must use only that data and say when something is missing. Tested with 19 questions: from 3 correct answers without data to about 16 with data. Developer only for now (the database is not distributed). Commands: `data-check`, `--no-data`, `--show-data`.
- Added: more verified data from wowdata: zone level ranges and zones for your level, dungeon levels, bosses and dungeons for your level, experience to the next level, quest experience and objectives, item drops from `v_botin`, flights from a place with their cost and transports. Travel route questions are answered as missing data until the routes are in the database (never searched on the internet). Second battery of 15 questions: 14 with correct data, the route one answered honestly as missing.
- Added: WoW Forever dungeon level ranges provided by the maintainer (`companion/askforever/data/forever_dungeon_levels.json`, including Scarlet Monastery wings and Stratholme entrances); they take precedence over the client values.
- Added: conversation memory: questions asked while the addon window stays open are chained (the addon sends a conversation number that changes when the window is closed after asking); follow-up questions reuse the data of the previous one.
- Added: level panorama in every question (zones and dungeons for your level), removing the zones the player excludes.
- Changed: more useful prompt: concrete recommendations from the data, one sentence for what is missing, never refers to guides and never names places that are not in the data.
- Fixed: the answer overlay no longer flashes over the game (it hides with transparency instead of unmapping).
- Added: travel routes computed from the database: flights and transports from wowdata (including trips recorded in the game, such as the Stormwind - Darkshore boat) plus the Deeprun Tram confirmed by the maintainer; the fastest route is described step by step with an approximate time; questions like "is there a boat from X to Y?" are answered from the data. Routes and transports never come from the internet or from the model's general knowledge.
- Added: warcraft.wiki.gg fallback when the database has no data for the question (not for travel): short English searches, preference for WoW Forever pages, answers say "according to the wiki" and show the sources; if neither the database nor the wiki has it, the AI says so without naming places. `--no-web` disables it.
- Fixed: profession questions (fishing, first aid, skinning...) no longer trigger the class spells or trainers.
- Changed: answers follow the language of the question; default temperature 0.2 (`ASKFOREVER_TEMPERATURE`).
- Added: guide to create free keys for each provider with verified links (`docs/API_KEYS.md`).
- Added: model comparison tool `bench`: runs 10 fixed WoW questions (zones, routes, class, dungeons, quests, honesty traps and an English question) against several providers/models and writes a Markdown + JSON report with latencies, errors and full answers to score by hand.
- Fixed: "and from here to X?" questions now compute the route from the player's position (before, no route was computed and the AI could make it up); travel questions whose places are not recognised are reported as missing data.
- Added: when the route starts somewhere else, the answer also gives the route from the player's position to that starting point (for example, the tram from Ironforge to Stormwind before the Darkshore boat).
- Added: routes take the known flight points into account when the addon sends them (`ctx.fp`, TaxiNodes IDs): flights only between known points, a note with the faster route once the missing points are discovered, and a reminder to discover the flight point at the destination. Without that list, the answer names the flight points the route uses and says how to register them.
- Fixed: generic words in place names ("valle", "bosque"...) no longer match other places by prefix (Coldridge Valley resolved to Astranaar); when origin and destination are in the same zone the answer says to walk; without the list of known flight points, a route without flights is also given.
- Fixed: capital city flight points are shown with the city name only (the client calls them "Stormwind, Elwynn" or "Ironforge, Dun Morogh", which made the AI say there was a flight point in Elwynn Forest); the walking note no longer says that two different zones are the same one.
- Fixed: the answer overlay could hang while the companion kept answering in the console. It now runs in a watched child process: if it stops responding for 10 s or dies, it is restarted and shows the last state again (at most 5 restarts every 5 minutes). Overlay errors are written to `addon/AskForever/dev/companion.log` (development folder, ignored by git and excluded from the release). `run --overlay-inprocess` keeps the old behaviour for diagnosis.
- Fixed: when the data did not answer the exact question (for example, whether dual specialization exists), the AI could state or deny game features from its general knowledge of other WoW versions. A new rule makes it say it does not have that information.
- Fixed: the packaged program could not read, save or delete the API key in the Windows Credential Manager (keyring did not find its backend inside the PyInstaller build), so it asked for the key again and the uninstaller left it behind. The release build now runs a smoke test of the packaged program that saves, reads and deletes a test key.
- Fixed: uninstalling while AskForever was open left the program and data folders behind; the uninstaller now closes it first and removes both folders completely, and updating closes it too. The installation guide shows the Windows SmartScreen warning.
- Fixed (development only): the report window did not take keyboard focus for the note.
- Changed: the experimental slot diagnostics (`/af slotprobe`, `/af slottest`) moved to the development folder; they are not part of the public addon.
- Added: Windows packaging built only on GitHub Actions: the companion as a PyInstaller folder app (no UPX) with a per-user Inno Setup installer (no administrator rights, Start menu shortcut, uninstaller that runs `uninstall --yes`). Pushing a `v*` tag builds, tests, hashes (SHA-256), attests the provenance and publishes the release with the installer and the addon zip; changes in `dev` only build test artifacts.
- Added: simple first run: starting the companion without arguments (double click) runs it; if there is no API key, a console wizard opens the key guide, asks for the key, tests it and saves it in the Windows Credential Manager (`setup` runs it again). `uninstall` removes the saved keys, the companion's data folder and the helper slot addons (never follows links outside their folders; `--addon` also removes the addon).
- Added: game data downloader in the companion: downloads the game database published on GitHub Releases (`data-YYYY.MM.DD`), checks its SHA-256 and integrity and installs it atomically in `%LOCALAPPDATA%\AskForever\data` (keeping a backup); `update-data` command and `--no-update` option. The developer's own wowdata database is never replaced. Next: updates through the CurseForge addon.
- Added: public continuous integration on GitHub Actions: companion tests on Windows, CodeQL code scanning and Dependabot updates, with CI, CodeQL, license and release badges and links to the security page in the README.
- Added: security and transparency page (`docs/SECURITY_TRANSPARENCY.md`, `docs/SEGURIDAD_TRANSPARENCIA.md`), checked against the code: what the companion does and never does, every network connection, the data sent to the AI, the files and settings it touches, how to verify it and why Windows may show a warning. `SECURITY.md` explains how to report a security problem.
- Fixed: answers based on the (English) wiki used English names in Spanish answers. The AI now receives the official Spanish names found in wowdata for the names in the wiki excerpts (for example "Well Fed = Bien alimentado") and must use them; untranslated names are quoted and marked as English.
- Added (development only): "Informe" button in the AskForever window that sends a report message (with the note typed in the box) to the companion, which writes a plain text file in `addon/AskForever/dev/informes/` with the last question, player context, data given to the AI, model, time and answer. The button opens its own window with the last question and a box to describe what is wrong (an empty report asks for confirmation). The window also lists the open reports, each with a Close button that asks the companion to delete its file (strictly validated id, only inside the reports folder). It lives in `addon/AskForever/dev/`, which `build-release.ps1` leaves out of the public zip (and fails if anything from it slips in).
- Added (addon): known flight points are saved per character when a flight master's map is opened and sent with each question (`fp`); a chat line confirms new points. The last reading is kept in `AskForeverDB.flightsDebug` to check which taxi API the client has.

### Español
- Añadido: el companion admite varios proveedores de IA en la nube compatibles con OpenAI (Gemini, Groq, Mistral, Cerebras, OpenRouter), con una clave y un modelo por proveedor, y los comandos `providers`, `list-models` y las opciones `--provider` / `--model`.
- Añadido: datos de juego verificados desde una base local de wowdata (solo lectura): misiones (quién la da, dónde se entrega, objetivos), posiciones de PNJ, hechizos de instructor e instructores, entradas de mazmorras, puntos de vuelo, ramas de talentos y origen de objetos se detectan en la pregunta y se pasan a la IA, que debe usar solo esos datos y decir cuándo falta algo. Probado con 19 preguntas: de 3 respuestas correctas sin datos a unas 16 con datos. Por ahora solo para desarrollo (la base no se distribuye). Comandos: `data-check`, `--no-data`, `--show-data`.
- Añadido: más datos verificados de wowdata: niveles de zona y zonas para tu nivel, nivel, jefes y mazmorras para tu nivel, experiencia hasta el siguiente nivel, experiencia y objetivos de misión, botín desde `v_botin`, vuelos desde un lugar con su coste y transportes. Las preguntas de rutas de viaje se responden como dato ausente hasta que las rutas estén en la base (nunca se buscan en internet). Segunda batería de 15 preguntas: 14 con datos correctos y la de ruta respondida honestamente como ausente.
- Añadido: rangos de nivel de las mazmorras de WoW Forever facilitados por el mantenedor (`companion/askforever/data/forever_dungeon_levels.json`, con las alas del Monasterio Escarlata y las entradas de Stratholme); mandan sobre los valores del cliente.
- Añadido: memoria de conversación: las preguntas hechas mientras la ventana del addon sigue abierta se encadenan (el addon manda un número de conversación que cambia al cerrarla tras preguntar); las preguntas de seguimiento reutilizan los datos de la anterior.
- Añadido: panorama del nivel en cada pregunta (zonas y mazmorras para tu nivel), quitando las zonas que el jugador descarta.
- Cambiado: prompt más útil: recomendaciones concretas con los datos, una frase para lo que falta, nunca remite a guías ni nombra lugares que no estén en los datos.
- Corregido: el overlay de respuesta ya no parpadea sobre el juego (se oculta con transparencia en lugar de desmapearse).
- Añadido: rutas de viaje calculadas con la base: vuelos y transportes de wowdata (incluidos los viajes grabados en el juego, como el barco Ventormenta - Costa Oscura) más el Tranvía Subterráneo confirmado por el mantenedor; la ruta más rápida se describe paso a paso con un tiempo aproximado; preguntas como «¿hay barco de X a Y?» se responden con los datos. Las rutas y los transportes nunca salen de internet ni del conocimiento general del modelo.
- Añadido: respaldo de warcraft.wiki.gg cuando la base no tiene datos para la pregunta (no para viajes): búsquedas cortas en inglés, preferencia por las páginas de WoW Forever, las respuestas dicen «según la wiki» y muestran las fuentes; si ni la base ni la wiki lo tienen, la IA lo dice sin nombrar lugares. `--no-web` lo desactiva.
- Corregido: las preguntas de profesiones (pesca, primeros auxilios, desuello…) ya no activan los hechizos ni los instructores de la clase.
- Cambiado: las respuestas siguen el idioma de la pregunta; temperatura por defecto 0,2 (`ASKFOREVER_TEMPERATURE`).
- Añadido: guía para crear claves gratuitas de cada proveedor con enlaces comprobados (`docs/CLAVES_API.md`).
- Añadido: herramienta de comparación de modelos `bench`: lanza 10 preguntas fijas de WoW (zonas, rutas, clase, mazmorras, misiones, trampas de honestidad y una pregunta en inglés) a varios proveedores y modelos y genera un informe Markdown + JSON con latencias, errores y respuestas completas para puntuar a mano.
- Corregido: las preguntas del tipo «¿y de aquí a X?» calculan la ruta desde la posición del jugador (antes no se calculaba y la IA podía inventársela); las preguntas de viaje cuyos lugares no se reconocen se marcan como dato ausente.
- Añadido: cuando la ruta empieza en otro sitio, la respuesta da también la ruta desde la posición del jugador hasta ese origen (por ejemplo, el tranvía de Forjaz a Ventormenta antes del barco a Costa Oscura).
- Añadido: las rutas tienen en cuenta los puntos de vuelo conocidos cuando el addon los envía (`ctx.fp`, IDs de TaxiNodes): vuelos solo entre puntos conocidos, aviso con la ruta más rápida cuando se descubran los que faltan y recordatorio de descubrir el punto de vuelo del destino. Sin esa lista, la respuesta nombra los puntos de vuelo que usa la ruta y explica cómo registrarlos.
- Corregido: las palabras genéricas de los nombres de lugar («valle», «bosque»…) ya no casan por prefijo con otros lugares (el Valle de Crestanevada salía como Astranaar); si origen y destino están en la misma zona, la respuesta dice que se va a pie; sin la lista de puntos de vuelo conocidos, se da también la ruta sin vuelos.
- Corregido: los puntos de vuelo de las capitales se muestran solo con el nombre de la ciudad (el cliente los llama «Ventormenta, Elwynn» o «Forjaz, Dun Morogh» y la IA decía que había vuelo en el Bosque de Elwynn); la nota de ir a pie ya no dice que dos zonas distintas son la misma.
- Corregido: el overlay de respuesta podía colgarse mientras el companion seguía respondiendo en la consola. Ahora va en un proceso hijo vigilado: si deja de responder 10 s o muere, se reinicia y vuelve a mostrar el último estado (como mucho 5 reinicios cada 5 minutos). Los errores del overlay se escriben en `addon/AskForever/dev/companion.log` (carpeta de desarrollo, ignorada por git y fuera de la release). `run --overlay-inprocess` mantiene el comportamiento anterior para diagnosticar.
- Corregido: cuando los datos no respondían justo a lo preguntado (por ejemplo, si existe la doble especialización), la IA podía afirmar o negar funciones del juego con lo que sabe de otras versiones de WoW. Una regla nueva hace que diga que no tiene ese dato.
- Corregido: el programa empaquetado no podía leer, guardar ni borrar la clave en el Administrador de credenciales de Windows (keyring no encontraba su almacén dentro del empaquetado de PyInstaller), así que volvía a pedir la clave y el desinstalador no la borraba. La compilación de la versión ejecuta ahora una prueba del programa empaquetado que guarda, lee y borra una clave de prueba.
- Corregido: desinstalar con AskForever abierto dejaba las carpetas del programa y de los datos; ahora el desinstalador lo cierra antes y borra las dos carpetas por completo, y al actualizar también lo cierra. La guía de instalación muestra el aviso de Windows SmartScreen.
- Corregido (solo desarrollo): la ventana de informe no daba el foco del teclado al cuadro de la nota.
- Cambiado: los diagnósticos experimentales de slots (`/af slotprobe`, `/af slottest`) pasan a la carpeta de desarrollo; no forman parte del addon público.
- Añadido: empaquetado para Windows compilado solo en GitHub Actions: el companion como programa en carpeta de PyInstaller (sin UPX) con un instalador de Inno Setup por usuario (sin permisos de administrador, acceso en el menú Inicio y desinstalador que ejecuta `uninstall --yes`). Una etiqueta `v*` compila, prueba, calcula los SHA-256, atestigua la procedencia y publica la versión con el instalador y el zip del addon; los cambios en `dev` solo compilan artefactos de prueba.
- Añadido: primer arranque sencillo: abrir el companion sin argumentos (doble clic) lo pone en marcha; si no hay clave de la API, un asistente en la consola abre la guía, pide la clave, la prueba y la guarda en el Administrador de credenciales de Windows (`setup` lo repite). `uninstall` borra las claves guardadas, la carpeta de datos del companion y los addons auxiliares de slots (nunca sigue enlaces fuera de sus carpetas; `--addon` borra también el addon).
- Añadido: descargador de datos del juego en el companion: descarga la base publicada en GitHub Releases (`data-AAAA.MM.DD`), comprueba su SHA-256 y su integridad y la instala de golpe en `%LOCALAPPDATA%\AskForever\data` (con copia de seguridad); comando `update-data` y opción `--no-update`. La base de wowdata del desarrollador nunca se sustituye. Siguiente paso: actualizaciones a través del addon de CurseForge.
- Añadido: integración continua pública en GitHub Actions: pruebas del companion en Windows, análisis del código con CodeQL y actualizaciones de Dependabot, con etiquetas de CI, CodeQL, licencia y versión y enlaces a la página de seguridad en el README.
- Añadido: página de seguridad y transparencia (`docs/SECURITY_TRANSPARENCY.md`, `docs/SEGURIDAD_TRANSPARENCIA.md`), comprobada contra el código: qué hace el companion y qué no hace nunca, todas las conexiones de red, los datos que se envían a la IA, los archivos y ajustes que toca, cómo comprobarlo y por qué Windows puede mostrar un aviso. `SECURITY.md` explica cómo avisar de un problema de seguridad.
- Corregido: las respuestas basadas en la wiki (en inglés) usaban nombres en inglés en respuestas en español. La IA recibe ahora los nombres oficiales en español que hay en wowdata para los nombres de los extractos de la wiki (por ejemplo «Well Fed = Bien alimentado») y debe usarlos; los que no tienen traducción van entre comillas indicando que son el nombre en inglés.
- Añadido (solo desarrollo): botón «Informe» en la ventana de AskForever que envía al companion un mensaje de informe (con la nota escrita en la caja); el companion escribe un archivo de texto plano en `addon/AskForever/dev/informes/` con la última pregunta, el contexto del jugador, los datos que recibió la IA, el modelo, el tiempo y la respuesta. El botón abre una ventana propia con la última pregunta y un cuadro para escribir qué está mal (un informe vacío pide confirmación). La ventana también lista los informes abiertos, cada uno con un botón Cerrar que pide al companion borrar su archivo (identificador validado y solo dentro de la carpeta de informes). Vive en `addon/AskForever/dev/`, que `build-release.ps1` deja fuera del zip público (y falla si se cuela algo).
- Añadido (addon): los puntos de vuelo conocidos se guardan por personaje al abrir el mapa de un maestro de vuelo y se envían con cada pregunta (`fp`); una línea en el chat confirma los nuevos. La última lectura queda en `AskForeverDB.flightsDebug` para comprobar qué API de taxi trae el cliente.

## [0.2.0-beta.1] - 2026-11-14

Milestone 2: the first end-to-end answer. Tested in WoW Forever (1920x1080, borderless window): the pixel strip is read with 0 errors and a question reaches the companion in about 200 ms. Minor bump: new functionality, backwards compatible. Developer preview: the companion runs from source (no installer yet, planned for 0.4.0) and is not yet part of the CurseForge package.

### English
- Added: the chat window now also sends the question and the character context to the companion through a strip of colored blocks in the top-left corner of the screen (pixel-exact, CRC-32, paginated, only outside combat). No input is simulated and no memory is read.
- Added: companion (Python): finds the game window, captures and decodes the strip, reassembles messages without duplicates, asks Google Gemini and shows the answer in a click-through overlay that never takes focus. Commands: `run`, `listen`, `ask`, `overlay-demo`, `set-key`, `test-key`.
- Added: OpenAI-compatible provider layer with retries on rate limits and readable errors; the key is kept in the Windows Credential Manager. Default model `gemini-3.5-flash-lite` (about 1 s); `gemini-3.8-flash`, `3.7-flash` and `flash-latest` did not answer within 60 s on the free plan when tested.
- Added: `/af pattern` (shows a test pattern for 10 seconds) and `/af selftest` (checks the protocol) as diagnostics.
- Added: step-by-step guide to create and store a free Google Gemini key (`docs/GEMINI_KEY.md`).
- Known limits: no memory between questions, no profession/talent/inventory data and no verified game data yet, so answers can be wrong; answers appear in an overlay, not in the addon window.

### Español
Milestone 2: la primera respuesta de extremo a extremo. Probado en WoW Forever (1920x1080, ventana sin bordes): la tira de píxeles se lee con 0 errores y una pregunta llega al companion en unos 200 ms. Subida menor: funcionalidad nueva, compatible. Versión para desarrolladores: el companion se ejecuta desde el código (aún sin instalador, previsto para la 0.4.0) y todavía no forma parte del paquete de CurseForge.

- Añadido: la ventana de chat ahora también envía la pregunta y el contexto del personaje al companion con una tira de bloques de color en la esquina superior izquierda de la pantalla (píxel exacto, CRC-32, paginada, solo fuera de combate). No simula teclas ni lee memoria.
- Añadido: companion (Python): localiza la ventana del juego, captura y decodifica la tira, reensambla los mensajes sin duplicados, pregunta a Google Gemini y muestra la respuesta en un overlay que deja pasar los clics y nunca roba el foco. Comandos: `run`, `listen`, `ask`, `overlay-demo`, `set-key`, `test-key`.
- Añadido: capa de proveedor compatible con OpenAI con reintentos ante límites y errores legibles; la clave se guarda en el Administrador de credenciales de Windows. Modelo por defecto `gemini-3.5-flash-lite` (alrededor de 1 s); `gemini-3.8-flash`, `3.7-flash` y `flash-latest` no respondieron en 60 s en el plan gratuito durante la prueba.
- Añadido: `/af pattern` (muestra un patrón de prueba 10 segundos) y `/af selftest` (comprueba el protocolo) como diagnóstico.
- Añadido: guía paso a paso para crear y guardar una clave gratuita de Google Gemini (`docs/CLAVE_GEMINI.md`).
- Límites conocidos: sin memoria entre preguntas, sin datos de profesiones, talentos ni inventario y sin datos de juego verificados, así que las respuestas pueden ser erróneas; la respuesta sale en un overlay, no en la ventana del addon.

## [0.1.0-beta.1] - 2026-11-13

First working addon (milestone 1). Tested in WoW Forever (interface 16001); not published on CurseForge yet. Minor bump: first functionality, backwards compatible.

### English
- Added: chat window in the native Lorewake/FishForever style (portrait frame, dark panels), opened with `/af`, `/askforever`, a configurable keybind or the minimap button.
- Added: character context collection (level, race, class, faction, zone, subzone, coordinates, active quests with level).
- Added: **Copy prompt** button: builds a ready-to-use prompt with that context and shows it selected for `Ctrl+C`.
- Added: draggable minimap button (`/af minimap` shows or hides it), `/af help` and `/af reset`.
- Added: English and Spanish locales (`esES` also for `esMX`).
- Added: own icon (speech bubble with a question mark) for the window portrait, minimap button and addon list; `scripts/make-icons.py` regenerates it.
- Added: `scripts/build-release.ps1` (builds the CurseForge zip, checks the `.toc`) and `docs/CURSEFORGE.md` (page texts and checklist).

### Español
Primer addon funcional (milestone 1). Probado en WoW Forever (interfaz 16001); todavía sin publicar en CurseForge. Subida menor: primera funcionalidad, compatible.

- Añadido: ventana de chat con el estilo nativo de Lorewake/FishForever (marco con retrato, paneles oscuros), que se abre con `/af`, `/askforever`, un atajo configurable o el botón del minimapa.
- Añadido: recogida del contexto del personaje (nivel, raza, clase, facción, zona, subzona, coordenadas, misiones activas con nivel).
- Añadido: botón **Copiar prompt**: construye un prompt listo para usar con ese contexto y lo muestra seleccionado para `Ctrl+C`.
- Añadido: botón de minimapa arrastrable (`/af minimap` lo muestra u oculta), `/af help` y `/af reset`.
- Añadido: idiomas inglés y español (`esES` también para `esMX`).
- Añadido: icono propio (bocadillo con interrogación) para el retrato de la ventana, el botón del minimapa y la lista de addons; `scripts/make-icons.py` lo regenera.
- Añadido: `scripts/build-release.ps1` (genera el zip para CurseForge y comprueba el `.toc`) y `docs/CURSEFORGE.md` (textos de la página y lista de comprobación).

## [0.0.1] - 2026-11-13

First release: documentation only, no addon or companion yet.

### English
- Added: README, ROADMAP, TODO, installation guides (EN/ES), CC BY-NC 4.0 license and folder structure.
- Added: `scripts/dev-link.ps1` to symlink the addon into the game client during development.

### Español
Primera publicación: solo documentación, sin addon ni companion todavía.

- Añadido: README, ROADMAP, TODO, guías de instalación (EN/ES), licencia CC BY-NC 4.0 y estructura de carpetas.
- Añadido: `scripts/dev-link.ps1` para enlazar el addon al cliente durante el desarrollo.
