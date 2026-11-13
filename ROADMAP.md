# AskForever — Roadmap / Hoja de ruta

**[English](#english) · [Español](#español)**

---

## English

Continuous development with **one beta release per day**. Each milestone can be released on its own. If a milestone does not fit in a day, the stable part ships and the rest moves to the next one.

Legend: ⬜ pending · 🟨 in progress · ✅ released

- ⬜ **v0.1.0-beta — Addon base + "Copy prompt".** First useful release, no companion. Chat window, `/askforever` and `/af`, configurable keybind, character context (level, race, class, faction, zone, subzone, coordinates, active quests), **Copy prompt** button (EditBox with the prompt selected for Ctrl+C), `esES`/`esMX` and `enUS` locales, minimap button. *Done when:* it loads in Forever with no errors and the prompt carries the right context.
- ⬜ **v0.2.0-beta — Transport test (outbound) + overlay answer.** Pixel strip from the addon (header, length, sequence, CRC32) shown only while a message is pending; CLI companion that captures and decodes it, ACKs, calls Gemini (OpenAI-compatible endpoint) and shows the answer in an overlay window; API key stored with `keyring`. *Done when:* 20 consecutive questions with no loss, outbound latency under 1 s, error 429 handled. ⚠️ Decision point: if capture does not work in Forever, the plan is reconsidered here.
- ⬜ **v0.3.0-beta — Answer inside the game (return path via LoD slots).** `askforever dev-setup` generates the `AskForever_SlotNNN` addon pool; the addon polls and loads free slots with `C_AddOns.LoadAddOn` and renders the answer; automatic fallback to the overlay. *Done when:* the answer is visible in game without `/reload`, 3–10 s in total.
- ⬜ **v0.4.0-beta — Installer and first-run wizard.** PyInstaller `.exe`: detects `_forever_`, asks for and tests the API key, creates the slots, adds itself to startup, tray icon; `/af test` end-to-end self-diagnosis. *Done when:* clean install on Windows without Python in under 5 minutes.
- ⬜ **v0.5.0-beta — Reliable routes + "Take me there".** `data/routes.json` zone graph (level ranges, faction, boats, zeppelins, on foot, flights); intent router → Dijkstra with level/faction penalties → LLM writes the answer; map pins and arrow. *Done when:* 30 test route questions are correct for both factions.
- ⬜ **v0.6.0-beta — Natural conversation and robustness.** Conversation memory, queueing during combat / chat lockdown, answers with source and confidence, "I don't know" mode.
- ⬜ **v0.7.0-beta — Multi-provider.** Companion selector: Gemini (free) · OpenAI-compatible · Claude (API key) · Ollama.
- ⬜ **v0.8.0+ — Content.** Quests, NPCs, farming and professions, guide RAG.
- ⬜ **v1.0.0 — Stable release.** Full EN/ES guides with screenshots, final CurseForge page, short demo video.

---

## Español

Desarrollo continuo con **una beta al día**. Cada hito se puede publicar por sí solo. Si un hito no cabe en el día, se publica la parte estable y el resto pasa al siguiente.

Leyenda: ⬜ pendiente · 🟨 en curso · ✅ publicado

- ⬜ **v0.1.0-beta — Addon base + «Copiar prompt».** Primera versión útil, sin companion. Ventana de chat, `/askforever` y `/af`, atajo configurable, contexto del personaje (nivel, raza, clase, facción, zona, subzona, coordenadas, misiones activas), botón **Copiar prompt** (EditBox con el prompt seleccionado para Ctrl+C), locales `esES`/`esMX` y `enUS`, botón de minimapa. *Terminado cuando:* carga en Forever sin errores y el prompt lleva el contexto correcto.
- ⬜ **v0.2.0-beta — Prueba de transporte (ida) + respuesta en overlay.** Tira de píxeles del addon (cabecera, longitud, secuencia, CRC32) visible solo con mensaje pendiente; companion CLI que la captura y decodifica, envía ACK, llama a Gemini (endpoint compatible con OpenAI) y muestra la respuesta en una ventana overlay; clave guardada con `keyring`. *Terminado cuando:* 20 preguntas seguidas sin pérdidas, latencia de ida < 1 s, error 429 gestionado. ⚠️ Punto de decisión: si la captura no funciona en Forever, aquí se replantea el plan.
- ⬜ **v0.3.0-beta — Respuesta dentro del juego (vuelta por slots LoD).** `askforever dev-setup` genera el pool de addons `AskForever_SlotNNN`; el addon sondea, carga los libres con `C_AddOns.LoadAddOn` y pinta la respuesta; respaldo automático al overlay. *Terminado cuando:* la respuesta se ve en el juego sin `/reload`, 3–10 s en total.
- ⬜ **v0.4.0-beta — Instalador y asistente de primera ejecución.** `.exe` con PyInstaller: detecta `_forever_`, pide y prueba la clave, crea los slots, se añade al arranque, icono en bandeja; `/af test` autodiagnostica de extremo a extremo. *Terminado cuando:* instalación limpia en un Windows sin Python en menos de 5 minutos.
- ⬜ **v0.5.0-beta — Rutas fiables + «Llévame».** Grafo de zonas `data/routes.json` (rangos de nivel, facción, barcos, zepelines, a pie, vuelos); router de intención → Dijkstra con penalización por nivel/facción → el LLM redacta; pines en el mapa y flecha. *Terminado cuando:* 30 preguntas de ruta de prueba correctas para ambas facciones.
- ⬜ **v0.6.0-beta — Conversación natural y robustez.** Memoria de conversación, cola en combate / bloqueo de chat, respuestas con fuente y confianza, modo «no lo sé».
- ⬜ **v0.7.0-beta — Multi-proveedor.** Selector en el companion: Gemini (gratis) · compatible con OpenAI · Claude (clave de API) · Ollama.
- ⬜ **v0.8.0+ — Contenido.** Misiones, NPCs, farmeo y profesiones, RAG de guías.
- ⬜ **v1.0.0 — Lanzamiento estable.** Guías EN/ES completas con capturas, página final de CurseForge, vídeo corto de demo.
