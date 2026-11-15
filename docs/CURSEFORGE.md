# CurseForge — publication kit / Kit de publicación

**[English](#english) · [Español](#español)**

Texts to paste into the CurseForge project and into each file upload. Nothing here is published automatically: the upload is manual, from the project owner's account.
Textos para pegar en el proyecto de CurseForge y en cada subida de archivo. Nada se publica solo: la subida es manual, desde la cuenta del propietario.

Current version / Versión actual: **0.3.0-beta.3 (Beta 4)**, 2026-11-15. The 0.3.0-beta.1 was never uploaded to CurseForge; Beta 3 includes it. / La 0.3.0-beta.1 no se subió a CurseForge; la Beta 3 la incluye.

---

## English

### Every new version (update)
The CurseForge project already exists: a new version is just a **file upload** to it.

1. The GitHub release is created by the release workflow when the `v<version>` tag is pushed (installer, addon zip, SHA-256 hashes and build provenance). Nothing is built locally.
2. Download the addon zip from that release: `https://github.com/warcrafted-server/AskForever/releases/download/v<version>/AskForever-<version>.zip`
3. On CurseForge: **Files → Upload File**.
   - **File:** the zip from step 2.
   - **Display name:** `AskForever <version> (Beta N)`, where N counts the betas published on CurseForge (0.3.0-beta.2 is Beta 3, 0.3.0-beta.3 is Beta 4). The version number must stay exactly as in the addon and GitHub, so players can report which one they have.
   - **Release type:** Beta (Release once there is a stable 1.0).
   - **Game version:** Forever.
   - **Changelog:** the file changelog of that version (below), written for players, without development details.
4. If the features changed, update the **summary** and the **description** with the texts below.

### Project fields (set once; review when features change)
| Field | Value |
|---|---|
| Name | AskForever |
| Summary | Ask inside WoW Forever and get the answer over the game in seconds, with verified game data. |
| Author | WarCrafted |
| License | Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0); if it is not offered, "Custom" with the text of `LICENSE` |
| Source | https://github.com/warcrafted-server/AskForever |
| Issues | https://github.com/warcrafted-server/AskForever/issues |
| Logo | `docs/img/logo.png` (400x400) |
| Screenshots | `docs/img/v0.2.0-overlay.png`, `docs/img/v0.2.0-window.png`, `docs/img/v0.3.0-install-first-run.png`, `docs/img/v0.3.0-quest-items.png` |

In the description, link only to pages of the GitHub project (no direct download links).

### Description (English and Spanish, paste as is)

```markdown
**AskForever** lets you ask questions inside WoW Forever and shows the answer over the game in seconds, using verified data from the game database.

## What it does
- Ask with `/af` or the minimap button; the answer appears over the game, on the right.
- Uses verified game data: quests, NPCs, class trainers, dungeons and their levels, zones for your level, loot and flight points.
- Travel routes with flights, boats, zeppelins and the Deeprun Tram, starting from where you are.
- Remembers the conversation, so follow-up questions work ("and from here?").
- Says "I don't know" instead of guessing. English and Spanish.

## How to install (about 10 minutes, once)
1. Install this addon.
2. Install the free **AskForever companion** for Windows from the [project page on GitHub](https://github.com/warcrafted-server/AskForever) (Releases).
3. Open AskForever: the first time, an assistant helps you get a free Google Gemini key and downloads the game data.
4. Keep the AskForever window open while you play.

The first time you enter the game, a welcome window shows these steps with the links; `/af help` or the **?** button opens it again. The addon folder also includes the installation guide and the security and transparency report (`docs/`).

Step-by-step guide with screenshots: [installation guide](https://github.com/warcrafted-server/AskForever/blob/main/docs/INSTALL_GUIDE.md).

## Privacy and security
- It does not read game memory and does not automate anything: no keys pressed, no mouse moved.
- It only talks to the AI provider you choose, the wiki when needed, and GitHub to download the game data.
- Your key is stored in the Windows Credential Manager, never in a file.
- The companion is built on GitHub from the public code, with SHA-256 hashes and build provenance. Windows may warn about it because it is not sold in the Microsoft Store: see [security and transparency](https://github.com/warcrafted-server/AskForever/blob/main/docs/SECURITY_TRANSPARENCY.md).

## Beta limitations
- The answer appears in a small window over the game, not yet inside the addon window.
- Use Windowed or Windowed (Fullscreen) display mode.

AI answers can contain mistakes: double-check important details in game.

---

**AskForever** te permite preguntar dentro de WoW Forever y ver la respuesta sobre el juego en segundos, con datos verificados de la base del juego.

## Qué hace
- Pregunta con `/af` o el botón del minimapa; la respuesta aparece sobre el juego, a la derecha.
- Usa datos verificados del juego: misiones, PNJ, instructores de clase, mazmorras y sus niveles, zonas para tu nivel, botín y puntos de vuelo.
- Rutas de viaje con vuelos, barcos, zepelines y el Tranvía Subterráneo, desde donde estás.
- Recuerda la conversación, así que puedes seguir preguntando («¿y desde aquí?»).
- Dice «no lo sé» en lugar de inventar. Inglés y español.

## Cómo se instala (unos 10 minutos, una vez)
1. Instala este addon.
2. Instala el **companion de AskForever**, gratuito, para Windows, desde la [página del proyecto en GitHub](https://github.com/warcrafted-server/AskForever) (Releases).
3. Abre AskForever: la primera vez, un asistente te ayuda a conseguir una clave gratuita de Google Gemini y descarga los datos del juego.
4. Deja la ventana de AskForever abierta mientras juegas.

La primera vez que entras al juego, una ventana de bienvenida muestra estos pasos con los enlaces; `/af help` o el botón **?** la vuelven a abrir. La carpeta del addon incluye también la guía de instalación y el informe de seguridad y transparencia (`docs/`).

Guía paso a paso con capturas: [guía de instalación](https://github.com/warcrafted-server/AskForever/blob/main/docs/GUIA_INSTALACION.md).

## Privacidad y seguridad
- No lee la memoria del juego ni automatiza nada: no pulsa teclas ni mueve el ratón.
- Solo habla con el proveedor de IA que elijas, con la wiki cuando hace falta y con GitHub para descargar los datos del juego.
- Tu clave se guarda en el Administrador de credenciales de Windows, nunca en un archivo.
- El companion se compila en GitHub desde el código público, con hashes SHA-256 y prueba de procedencia. Windows puede avisar porque no se vende en la Microsoft Store: consulta [seguridad y transparencia](https://github.com/warcrafted-server/AskForever/blob/main/docs/SEGURIDAD_TRANSPARENCIA.md).

## Limitaciones de la beta
- La respuesta aparece en una ventanita sobre el juego, todavía no dentro de la ventana del addon.
- Usa el modo de pantalla Ventana o Pantalla completa (ventana).

Las respuestas de la IA pueden contener errores: comprueba lo importante en el juego.

*World of Warcraft is a trademark of Blizzard Entertainment, Inc. Not affiliated with Blizzard. / World of Warcraft es una marca de Blizzard Entertainment, Inc. Sin afiliación con Blizzard.*
```

### File changelogs (paste in the upload form)

#### 0.3.0-beta.3 (Beta 4)

```markdown
**Beta 4 — better quest answers and a calmer answer window.**

- Improved: questions about a quest now say where to get what it asks for: which NPC drops each item (with coordinates and drop rate), which chest, crate or plant gives it, and where the creatures to kill are.
- Improved: you can ask without the quest name ("who drops the book?", "where are those kobolds?"): AskForever uses your active quests when the match is clear.
- Improved: quests that share a name are told apart with your quest log.
- Fixed: the answer window no longer flashes or takes the focus from the game, and it hides while the game is minimized or in the background.

**Beta 4: mejores respuestas de misiones y una ventana de respuesta más discreta.**

- Mejorado: las preguntas sobre una misión dicen dónde conseguir lo que pide: qué PNJ suelta cada objeto (con coordenadas y probabilidad), qué cofre, caja o planta lo da y dónde están las criaturas que hay que matar.
- Mejorado: puedes preguntar sin el nombre de la misión («¿quién suelta el libro?», «¿dónde están esos kóbolds?»): AskForever usa tus misiones activas cuando la coincidencia es clara.
- Mejorado: las misiones que comparten nombre se distinguen con tu registro de misiones.
- Corregido: la ventana de respuesta ya no parpadea ni le quita el foco al juego, y se oculta mientras el juego está minimizado o en segundo plano.
```

#### 0.3.0-beta.2 (Beta 3)

```markdown
**Beta 3 — AskForever now answers inside the game.**

- New: free Windows companion with a simple installer (GitHub Releases). Ask with `/af` or the minimap button and the answer appears over the game in seconds.
- New: the first time you enter the game, a welcome window explains what you need (the companion and a free Google Gemini key) with the links ready to copy. Open it again with `/af help` or the **?** button.
- New: first-run assistant in the companion for the free Google Gemini key (saved in the Windows Credential Manager, never in a file).
- New: verified data from the game database: quests, NPCs, class trainers, dungeons and their levels, zones for your level, loot and flight points.
- New: travel routes with flights, boats, zeppelins and the Deeprun Tram, starting from where you are, and a reminder to discover flight points.
- New: conversation memory: follow-up questions like "and from here?" use the previous answer.
- New: the addon folder includes `README.txt`, the installation guide and the security and data transparency report (`docs/`).
- Improved: answers follow the language of your question, use the official Spanish names and say "I don't know" instead of guessing.
- Security: the companion is built on GitHub from the public code, with SHA-256 hashes and build provenance. See the security and transparency page on GitHub.

**Beta 3: AskForever ahora responde dentro del juego.**

- Nuevo: companion gratuito para Windows con instalador sencillo (GitHub Releases). Pregunta con `/af` o el botón del minimapa y la respuesta aparece sobre el juego en segundos.
- Nuevo: la primera vez que entras al juego, una ventana de bienvenida explica lo que necesitas (el companion y una clave gratuita de Google Gemini) con los enlaces listos para copiar. Vuelve a abrirla con `/af help` o el botón **?**.
- Nuevo: asistente del primer arranque en el companion para la clave gratuita de Google Gemini (se guarda en el Administrador de credenciales de Windows, nunca en un archivo).
- Nuevo: datos verificados de la base del juego: misiones, PNJ, instructores de clase, mazmorras y sus niveles, zonas para tu nivel, botín y puntos de vuelo.
- Nuevo: rutas de viaje con vuelos, barcos, zepelines y el Tranvía Subterráneo, desde donde estás, y aviso para descubrir puntos de vuelo.
- Nuevo: memoria de conversación: preguntas de seguimiento como «¿y desde aquí?» tienen en cuenta la respuesta anterior.
- Nuevo: la carpeta del addon incluye `README.txt`, la guía de instalación y el informe de seguridad y transparencia de datos (`docs/`).
- Mejorado: las respuestas siguen el idioma de tu pregunta, usan los nombres oficiales en español y dicen «no lo sé» en lugar de inventar.
- Seguridad: el companion se compila en GitHub desde el código público, con hashes SHA-256 y prueba de procedencia. Consulta la página de seguridad y transparencia en GitHub.
```

---

## Español

### Cada versión nueva (actualización)
El proyecto de CurseForge ya existe: una versión nueva es solo **subir un archivo** a él.

1. La release de GitHub la crea el workflow de release al subir la etiqueta `v<versión>` (instalador, zip del addon, hashes SHA-256 y prueba de procedencia). No se compila nada en local.
2. Descarga el zip del addon de esa release: `https://github.com/warcrafted-server/AskForever/releases/download/v<versión>/AskForever-<versión>.zip`
3. En CurseForge: **Files → Upload File**.
   - **Archivo:** el zip del paso 2.
   - **Nombre visible:** `AskForever <versión> (Beta N)`, donde N cuenta las betas publicadas en CurseForge (la 0.3.0-beta.2 es la Beta 3 y la 0.3.0-beta.3 la Beta 4). El número de versión se mantiene exactamente igual que en el addon y en GitHub, para que los jugadores puedan decir cuál tienen.
   - **Tipo:** Beta (Release cuando haya una 1.0 estable).
   - **Versión del juego:** Forever.
   - **Registro de cambios:** el de esa versión (en la sección inglesa, bilingüe), escrito para el jugador, sin detalles de desarrollo.
4. Si cambian las funciones, actualiza el **resumen** y la **descripción** con los textos de la sección inglesa (la descripción ya es bilingüe).

### Campos del proyecto (se ponen una vez; revisarlos cuando cambien las funciones)
| Campo | Valor |
|---|---|
| Nombre | AskForever |
| Resumen | Ask inside WoW Forever and get the answer over the game in seconds, with verified game data. |
| Autor | WarCrafted |
| Licencia | Creative Commons Atribución-NoComercial 4.0 (CC BY-NC 4.0); si no aparece, «Custom» con el texto de `LICENSE` |
| Código | https://github.com/warcrafted-server/AskForever |
| Incidencias | https://github.com/warcrafted-server/AskForever/issues |
| Logo | `docs/img/logo.png` (400x400) |
| Capturas | `docs/img/v0.2.0-overlay.png`, `docs/img/v0.2.0-window.png`, `docs/img/v0.3.0-install-first-run.png`, `docs/img/v0.3.0-quest-items.png` |

En la descripción, enlaza solo a páginas del proyecto en GitHub (sin enlaces de descarga directa).
