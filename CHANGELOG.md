# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/). Versioning: [SemVer](https://semver.org/). English first, then Spanish / Inglés primero, después español.

## [Unreleased]

### English
- Added: the companion supports several OpenAI-compatible cloud providers (Gemini, Groq, Mistral, Cerebras, OpenRouter), one key and one model per provider, with `providers`, `list-models` and `--provider` / `--model` options.
- Added: guide to create free keys for each provider with verified links (`docs/API_KEYS.md`).
- Added: model comparison tool `bench`: runs 10 fixed WoW questions (zones, routes, class, dungeons, quests, honesty traps and an English question) against several providers/models and writes a Markdown + JSON report with latencies, errors and full answers to score by hand.

### Español
- Añadido: el companion admite varios proveedores de IA en la nube compatibles con OpenAI (Gemini, Groq, Mistral, Cerebras, OpenRouter), con una clave y un modelo por proveedor, y los comandos `providers`, `list-models` y las opciones `--provider` / `--model`.
- Añadido: guía para crear claves gratuitas de cada proveedor con enlaces comprobados (`docs/CLAVES_API.md`).
- Añadido: herramienta de comparación de modelos `bench`: lanza 10 preguntas fijas de WoW (zonas, rutas, clase, mazmorras, misiones, trampas de honestidad y una pregunta en inglés) a varios proveedores y modelos y genera un informe Markdown + JSON con latencias, errores y respuestas completas para puntuar a mano.

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
