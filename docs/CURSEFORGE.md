# CurseForge — publication kit / Kit de publicación

**[English](#english) · [Español](#español)**

Texts to paste into the CurseForge project page and file upload. Nothing here is published automatically: upload is manual, from the project owner's account.
Textos para pegar en la página del proyecto de CurseForge y en la subida del archivo. Nada se publica solo: la subida es manual, desde la cuenta del propietario.

---

## English

### Checklist
1. Run `.\scripts\build-release.ps1` → `release\AskForever-<version>.zip` (only the `AskForever/` folder).
2. Create the project on CurseForge (World of Warcraft addon, game version **Forever**; check the exact option offered in the upload form).
3. Paste the fields below, upload the screenshots from `docs/img/` and the zip.
4. Release type: **Beta**.
5. Only after it is live: tag `v<version>` and GitHub release (needs the owner's approval).

### Fields
- **Name:** AskForever
- **Summary (short):** Ask about WoW Forever and get a ready-to-use prompt with your character's context. Copy it to your favorite AI.
- **Author:** WarCrafted
- **License:** Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0). Pick the closest option offered or "Custom" with the text of `LICENSE`.
- **Source:** https://github.com/warcrafted-server/AskForever
- **Issues:** https://github.com/warcrafted-server/AskForever/issues
- **Screenshots:** `docs/img/v0.1.0-window.png`, `docs/img/v0.1.0-prompt.png`, `docs/img/v0.1.0-minimap.png`.

### Description
**AskForever** is the first step towards an AI assistant for WoW Forever that answers inside the game.

**What version 0.1 does (beta)**
- Opens a chat window with `/af`, a configurable keybind or the minimap button.
- Collects your character's context: level, race, class, faction, zone, coordinates and active quests with their levels.
- **Copy prompt** builds a ready-to-use prompt with that context, selected for `Ctrl+C`, so you can paste it into any AI chat (Gemini, ChatGPT, Claude…) without explaining who you are or where you are.
- English and Spanish.

**What it does not do yet**
Answers do not appear inside the game yet. That needs a small desktop companion app, planned for the next versions together with reliable zone-to-zone routes and a "Take me there" arrow. See the roadmap on the project page.

**Commands:** `/af` (open/close) · `/af help` · `/af reset` (re-center the window) · `/af minimap` (show/hide the button).

**Safe by design:** no simulated input, no memory reading, nothing is sent anywhere. The addon only uses the official addon API; you decide what to paste and where.

AI answers can contain mistakes: double-check important details in game.

*World of Warcraft is a trademark of Blizzard Entertainment, Inc. Not affiliated with Blizzard.*

### File changelog (paste in the upload form)
Beta 1: chat window, character context, Copy prompt button, minimap button, English and Spanish. Answers inside the game are not available yet.

---

## Español

### Lista de comprobación
1. Ejecuta `.\scripts\build-release.ps1` → `release\AskForever-<versión>.zip` (solo la carpeta `AskForever/`).
2. Crea el proyecto en CurseForge (addon de World of Warcraft, versión de juego **Forever**; comprueba la opción exacta que ofrezca el formulario).
3. Pega los campos de abajo, sube las capturas de `docs/img/` y el zip.
4. Tipo de versión: **Beta**.
5. Solo cuando esté publicado: tag `v<versión>` y release en GitHub (necesita la aprobación del propietario).

### Campos
- **Nombre:** AskForever
- **Resumen (corto):** Pregunta sobre WoW Forever y obtén un prompt listo con el contexto de tu personaje. Cópialo a tu IA favorita.
- **Autor:** WarCrafted
- **Licencia:** Creative Commons Atribución-NoComercial 4.0 (CC BY-NC 4.0). Elige la opción más parecida o «Custom» con el texto de `LICENSE`.
- **Código:** https://github.com/warcrafted-server/AskForever
- **Incidencias:** https://github.com/warcrafted-server/AskForever/issues
- **Capturas:** `docs/img/v0.1.0-window.png`, `docs/img/v0.1.0-prompt.png`, `docs/img/v0.1.0-minimap.png`.

### Descripción
**AskForever** es el primer paso hacia un asistente de IA para WoW Forever que responda dentro del juego.

**Qué hace la versión 0.1 (beta)**
- Abre una ventana de chat con `/af`, un atajo configurable o el botón del minimapa.
- Recoge el contexto de tu personaje: nivel, raza, clase, facción, zona, coordenadas y misiones activas con su nivel.
- **Copiar prompt** construye un prompt listo para usar con ese contexto, seleccionado para `Ctrl+C`, para pegarlo en cualquier chat de IA (Gemini, ChatGPT, Claude…) sin explicar quién eres ni dónde estás.
- Inglés y español.

**Qué no hace todavía**
Las respuestas aún no aparecen dentro del juego. Para eso hace falta un pequeño programa de escritorio (companion), previsto para las próximas versiones junto con rutas fiables entre zonas y una flecha «Llévame». Consulta la hoja de ruta en la página del proyecto.

**Comandos:** `/af` (abrir/cerrar) · `/af help` · `/af reset` (recentrar la ventana) · `/af minimap` (mostrar/ocultar el botón).

**Seguro por diseño:** no simula teclas, no lee la memoria del juego y no envía nada a ningún sitio. El addon solo usa la API oficial de addons; tú decides qué pegas y dónde.

Las respuestas de IA pueden contener errores: verifica lo importante en el juego.

*World of Warcraft es una marca de Blizzard Entertainment, Inc. Sin afiliación con Blizzard.*

### Registro de cambios del archivo (para el formulario)
Beta 1: ventana de chat, contexto del personaje, botón Copiar prompt, botón de minimapa, inglés y español. Las respuestas dentro del juego todavía no están disponibles.
