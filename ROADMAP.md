# AskForever — Roadmap / Hoja de ruta

**[English](#english) · [Español](#español)**

---

## English

Continuous development with frequent beta releases. Each milestone can be released on its own; if a milestone does not fit, the stable part ships and the rest moves to the next one. The order changed as we went: what was planned as 0.4 (installer) and 0.5 (routes) shipped in 0.3, and the answer inside the addon window moved later.

Legend: ⬜ pending · 🟨 in progress · ✅ released

- ✅ **v0.1.0-beta — Addon base + "Copy prompt".** Chat window, `/askforever` and `/af`, keybind, character context, Copy prompt, `esES`/`esMX` and `enUS`, minimap button.
- ✅ **v0.2.0-beta — Pixel strip + overlay answer (developer preview).** The addon sends the question as a pixel strip; the companion decodes it, asks the AI and shows the answer in an overlay over the game.
- ✅ **v0.3.0-beta.1 (CurseForge "Beta 3") — First functional public beta.** Windows installer built only on GitHub (SHA-256 hashes, build provenance), first-run key wizard and full uninstall; verified game data downloaded from GitHub; travel routes with flights, boats, zeppelins and the Deeprun Tram from the player's position; conversation memory; answers in the question's language with official Spanish names; "I don't know" instead of guessing; several AI providers; watched overlay process; security and transparency page.
- ⬜ **Next — Game data updates through CurseForge.** A cumulative data patch inside the addon (plain text), applied by the companion on top of the published base; new bases on GitHub only when the patch grows too much.
- ⬜ **Beginner's guide.** General WoW Forever knowledge (gameplay, interface, options, races, classes, professions…) verified against the game client, the client diagnostic, Blizzard and Wowhead; the AI only receives verified sections.
- ⬜ **Answer inside the addon window (return path via LoD "slot" addons).** The answer shows up in the addon's chat; the overlay stays as a fallback.
- ⬜ **"Take me there".** Map pins and arrow for routes and places.
- ⬜ **Robustness.** Queueing during combat / chat lockdown, other resolutions and interface scales, companion self-update.
- ⬜ **v1.0.0 — Stable release.** Complete EN/ES guides with screenshots, final CurseForge page, short demo video; Microsoft Store if the project is well received.

---

## Español

Desarrollo continuo con betas frecuentes. Cada hito se puede publicar por sí solo; si un hito no cabe, se publica la parte estable y el resto pasa al siguiente. El orden ha cambiado sobre la marcha: lo previsto como 0.4 (instalador) y 0.5 (rutas) salió en la 0.3, y la respuesta dentro de la ventana del addon pasa a más adelante.

Leyenda: ⬜ pendiente · 🟨 en curso · ✅ publicado

- ✅ **v0.1.0-beta — Addon base + «Copiar prompt».** Ventana de chat, `/askforever` y `/af`, atajo, contexto del personaje, Copiar prompt, `esES`/`esMX` y `enUS`, botón de minimapa.
- ✅ **v0.2.0-beta — Tira de píxeles + respuesta en overlay (versión para desarrolladores).** El addon envía la pregunta como una tira de píxeles; el companion la descodifica, pregunta a la IA y muestra la respuesta en un overlay sobre el juego.
- ✅ **v0.3.0-beta.1 («Beta 3» en CurseForge) — Primera beta pública funcional.** Instalador de Windows compilado solo en GitHub (hashes SHA-256, prueba de procedencia), asistente de la clave en el primer arranque y desinstalación completa; datos verificados del juego descargados de GitHub; rutas con vuelos, barcos, zepelines y el Tranvía Subterráneo desde la posición del jugador; memoria de conversación; respuestas en el idioma de la pregunta con los nombres oficiales en español; «no lo sé» en lugar de inventar; varios proveedores de IA; overlay en un proceso vigilado; página de seguridad y transparencia.
- ⬜ **Siguiente — Actualizaciones de datos por CurseForge.** Un parche de datos acumulado dentro del addon (texto plano) que el companion aplica sobre la base publicada; bases nuevas en GitHub solo cuando el parche crece demasiado.
- ⬜ **Guía de principiantes.** Conocimiento general de WoW Forever (jugabilidad, interfaz, opciones, razas, clases, profesiones…) verificado con el cliente del juego, el diagnóstico del cliente, Blizzard y Wowhead; la IA solo recibe las secciones verificadas.
- ⬜ **Respuesta dentro de la ventana del addon (vuelta por addons «slot» LoD).** La respuesta sale en el chat del addon; el overlay queda de respaldo.
- ⬜ **«Llévame».** Pines y flecha en el mapa para rutas y lugares.
- ⬜ **Robustez.** Cola en combate / bloqueo del chat, otras resoluciones y escalas de interfaz, autoactualización del companion.
- ⬜ **v1.0.0 — Lanzamiento estable.** Guías EN/ES completas con capturas, página final de CurseForge, vídeo corto de demo; Microsoft Store si el proyecto tiene buena acogida.
