# AskForever

[![CI](https://github.com/warcrafted-server/AskForever/actions/workflows/ci.yml/badge.svg)](https://github.com/warcrafted-server/AskForever/actions/workflows/ci.yml) [![CodeQL](https://github.com/warcrafted-server/AskForever/actions/workflows/codeql.yml/badge.svg)](https://github.com/warcrafted-server/AskForever/actions/workflows/codeql.yml) [![License: CC BY-NC 4.0](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey)](LICENSE) [![Latest release](https://img.shields.io/github/v/release/warcrafted-server/AskForever?include_prereleases)](https://github.com/warcrafted-server/AskForever/releases) [![VirusTotal](https://img.shields.io/badge/VirusTotal-v0.3.0--beta.3-blue)](https://www.virustotal.com/gui/file/882e541ae884519ebb20d147770122a857fb81c2f1f9ae8e477c12eb5ecfa077)

**[English](#english) · [Español](#español)**

[Security and transparency: what AskForever App does and never does](docs/SECURITY_TRANSPARENCY.md)

[Seguridad y transparencia: qué hace y qué no hace nunca AskForever App](docs/SEGURIDAD_TRANSPARENCIA.md)

---

## English

**AI assistant for WoW Forever.** Ask in plain language and get the answer over the game:

> *"How do I get from Westfall to The Barrens at a low level?"*

### What it does
AskForever knows your level, faction and zone, uses verified data from the game database (no guessing) and computes routes with flights and transports. The addon sends your question to **AskForever App**, which asks the AI and shows the answer over the game, on the right, for a few seconds.

![Answer about a quest: which NPC drops each item, with coordinates](docs/img/v0.3.0-quest-items.png)

### Status
**0.3.0-beta.4 (beta).** Quest questions say where to get each objective (drops, world objects, creatures) and understand your active quests. The addon and AskForever App for Windows work together: ask with `/af` or the minimap button and read the answer in game. Verified game data and routes with flights and transports are included. AskForever App has its own window and system-tray controls, a tested-in-app AI key setup dialog, and automatic app updates. Game data and guide cards are delivered with addon updates through CurseForge. English and Spanish.

See the [ROADMAP](ROADMAP.md), the [CHANGELOG](CHANGELOG.md) and the [TODO](TODO.md).

### Design principles
- **No simulated input and no memory reading.** The addon only uses the official addon API.
- WoW addons cannot access the Internet, so **AskForever App** connects the addon to the AI.
- AskForever App uses Google Gemini with a free key; other AI services are listed in the [API key guide](docs/API_KEYS.md).
- Languages: English and Spanish.

### Installation
1. **Addon:** install **AskForever** from the CurseForge app (select the **Forever** installation) or copy the `AskForever` folder from the addon zip into `World of Warcraft\_forever_\Interface\AddOns\`.
2. **AskForever App:** download the latest `AskForever-Setup-<version>.exe` from the [latest release](https://github.com/warcrafted-server/AskForever/releases/latest) and run it. It installs for your Windows user only, without administrator permission, and adds AskForever App to the Start menu.
3. **Free key:** open AskForever App. On first launch, its Configure AI dialog guides you through getting a free Google Gemini key (see the [Gemini key guide](docs/GEMINI_KEY.md)), tests it and saves it securely in Windows Credential Manager. The app downloads the base game database from GitHub when needed and applies the game data and guide cards included with the addon.

Keep AskForever App running while you play; closing its window sends it to the system tray, where you can reopen it or quit. The app updates itself and reopens after an update. Update game data and guide cards by updating the addon in CurseForge. The in-game chat can be scrolled with the mouse wheel or arrow buttons, and its window can be resized from the bottom-right corner.

The addon folder also includes `README.txt` and a `docs` folder with the installation guide and the security and data transparency report.

👉 **[Full installation guide](docs/INSTALL_GUIDE.md)**

### Development
Run `scripts\dev-link.ps1` to link this repository as a development copy. It appears in the AddOns list as **AskForever (dev)** and can coexist with the CurseForge install; enable only one at a time. Restart WoW completely the first time.

### Disclaimer
AI answers may contain mistakes; double-check important details in game. Blizzard has no official position on desktop apps such as AskForever: it is designed not to automate any gameplay action, but use it at your own risk.

---

## Español

**Asistente de IA para WoW Forever.** Pregunta en lenguaje natural y recibe la respuesta sobre el juego:

> *"¿Por dónde voy de Páramos de Poniente a Baldíos siendo nivel bajo?"*

### Qué hace
AskForever conoce tu nivel, facción y zona, usa datos verificados de la base de datos del juego (no inventa) y calcula rutas con vuelos y transportes. El addon envía tu pregunta a **AskForever App**, que consulta a la IA y muestra la respuesta sobre el juego, a la derecha, durante unos segundos.

![Respuesta sobre una misión: qué PNJ suelta cada objeto, con coordenadas](docs/img/v0.3.0-quest-items.png)

### Estado
**0.3.0-beta.4 (beta).** Las preguntas de misión dicen dónde conseguir cada objetivo (botín, objetos del mundo, criaturas) y entienden tus misiones activas. El addon y AskForever App para Windows funcionan juntos: pregunta con `/af` o el botón del minimapa y lee la respuesta dentro del juego. Incluye datos verificados del juego y rutas con vuelos y transportes. AskForever App tiene ventana y controles en la bandeja del sistema, un diálogo para configurar y probar la clave de IA, y actualizaciones automáticas de la app. Los datos del juego y las fichas llegan con las actualizaciones del addon desde CurseForge. Inglés y español.

Consulta la [hoja de ruta](ROADMAP.md), el [CHANGELOG](CHANGELOG.md) y el [TODO](TODO.md).

### Principios de diseño
- **No simula teclas ni lee la memoria del juego.** El addon solo usa la API oficial de addons.
- Los addons de WoW no pueden acceder a Internet, así que **AskForever App** conecta el addon con la IA.
- AskForever App usa Google Gemini con una clave gratuita; otros servicios de IA aparecen en la [guía de claves de API](docs/CLAVES_API.md).
- Idiomas: inglés y español.

### Instalación
1. **Addon:** instala **AskForever** desde la app de CurseForge (selecciona la instalación **Forever**) o copia la carpeta `AskForever` del zip del addon en `World of Warcraft\_forever_\Interface\AddOns\`.
2. **AskForever App:** descarga el último `AskForever-Setup-<versión>.exe` de la [última versión](https://github.com/warcrafted-server/AskForever/releases/latest) y ejecútalo. Se instala solo para tu usuario de Windows, sin permisos de administrador, y añade AskForever App al menú Inicio.
3. **Clave gratuita:** abre AskForever App. La primera vez, su diálogo Configurar IA te guía para conseguir una clave gratuita de Google Gemini (consulta la [guía de la clave de Gemini](docs/CLAVE_GEMINI.md)), la prueba y la guarda de forma segura en el Administrador de credenciales de Windows. La app descarga la base de datos del juego desde GitHub cuando hace falta y aplica los datos y las fichas incluidos con el addon.

Mantén AskForever App abierta mientras juegas; al cerrar su ventana queda en la bandeja del sistema, desde donde puedes volver a abrirla o salir. La app se actualiza sola y vuelve a abrirse al terminar. Para actualizar los datos y las fichas, actualiza el addon en CurseForge. El chat del juego se desplaza con la rueda del ratón o los botones de flecha y su ventana se puede cambiar de tamaño desde la esquina inferior derecha.

La carpeta del addon también incluye `README.txt` y una carpeta `docs` con la guía de instalación y el informe de seguridad y transparencia de datos.

👉 **[Guía de instalación completa](docs/GUIA_INSTALACION.md)**

### Desarrollo
Ejecuta `scripts\dev-link.ps1` para enlazar este repositorio como copia de desarrollo. Aparece en la lista de AddOns como **AskForever (desarrollo)** y puede convivir con la instalación de CurseForge; activa solo una a la vez. Reinicia WoW por completo la primera vez.

### Aviso
Las respuestas de IA pueden contener errores; verifica lo importante en el juego. Blizzard no tiene una postura oficial sobre programas de escritorio: AskForever está diseñado para no automatizar ninguna acción de juego, pero úsalo bajo tu responsabilidad.

---

**Author / Autor:** WarCrafted · warcrafted.server@gmail.com
**License / Licencia:** [CC BY-NC 4.0](LICENSE) · World of Warcraft is a trademark of Blizzard Entertainment, Inc. Not affiliated with Blizzard.
