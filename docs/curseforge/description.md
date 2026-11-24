**AskForever** lets you ask questions inside WoW Forever and shows the answer over the game in seconds, using verified game data. The addon works with **AskForever App** for Windows.

## What it does
- Ask with `/af` or the minimap button; the answer appears in the conversation of the addon window.
- Uses verified game data: quests, NPCs, class trainers, dungeons and their levels, zones for your level, loot and flight points.
- Quest help: where to get what a quest asks for (which NPC drops it, which chest or plant gives it, where the creatures to kill are), with coordinates. It understands your active quests, so "who drops the book?" is enough.
- Travel routes with flights, boats, zeppelins and the Deeprun Tram, starting from where you are.
- Class help from the current guides: talent builds, rotation, stats, enchants and leveling tips, plus professions, dungeons, raids and PvP.
- Knows your character: your talents and unspent points, professions, gear and stats, so you can ask "review my talents" or "where do I spend my next point?".
- Remembers the conversation, so follow-up questions work ("and from here?").
- Scroll the conversation with the mouse wheel or arrow buttons; resize the addon window from its bottom-right corner.
- Says "I don't know" instead of guessing. English and Spanish.
- Without AskForever App, **Copy prompt** copies the question with your context so you can paste it into any AI.
- Game data and guide cards arrive with addon updates through CurseForge.

## How to install (about 10 minutes, once)
1. Install this addon.
2. Install **AskForever App** for Windows from the [latest GitHub release](https://github.com/warcrafted-server/AskForever/releases/latest).
3. Open AskForever App. The first time, its **Configure AI** dialog helps you get a free Google Gemini key, tests it and saves it encrypted in Windows Credential Manager.
4. Keep AskForever App running while you play. Closing its window sends it to the system tray; quit from the tray menu when you are done.
5. AskForever App updates itself. To update game data and guide cards, update the addon in CurseForge; the app downloads a verified base database from GitHub when needed.

The first time you enter the game, a welcome window shows these steps with the links; `/af help` or the **?** button opens it again. The addon folder also includes the installation guide and the security and transparency report (`docs/`).

Step-by-step guide with screenshots: [installation guide](https://github.com/warcrafted-server/AskForever/blob/main/docs/INSTALL_GUIDE.md).

## Privacy and security
- It does not read game memory and does not automate anything: no keys pressed, no mouse moved.
- It contacts the configured AI provider and the wiki when needed. GitHub checks for app and data releases and downloads the app installer or base database; both are verified with SHA-256.
- With each question the addon sends the AI a summary of your character (level, class, zone, talents, professions, gear and stats). Nothing that identifies you is sent: no name, realm or gold.
- AskForever App reads the addon's game-data folder without modifying it. Your key is stored encrypted in Windows Credential Manager, never in a plain file.
- AskForever App is built on GitHub from the public code, with SHA-256 hashes and build provenance. Windows may show a warning the first time because the program is not code-signed: see [security and transparency](https://github.com/warcrafted-server/AskForever/blob/main/docs/SECURITY_TRANSPARENCY.md).

## Beta limitations
- AskForever App draws the answer over the addon window, so it hides while the game is minimized or in the background.

AI answers can contain mistakes: double-check important details in game.

---

**AskForever** te permite preguntar dentro de WoW Forever y ver la respuesta sobre el juego en segundos, con datos verificados del juego. El addon funciona con **AskForever App** para Windows.

## Qué hace
- Pregunta con `/af` o el botón del minimapa; la respuesta aparece en la conversación de la ventana del addon.
- Usa datos verificados del juego: misiones, PNJ, instructores de clase, mazmorras y sus niveles, zonas para tu nivel, botín y puntos de vuelo.
- Ayuda con misiones: dónde conseguir lo que pide una misión (qué PNJ lo suelta, qué cofre o planta lo da, dónde están las criaturas que hay que matar), con coordenadas. Entiende tus misiones activas, así que basta con «¿quién suelta el libro?».
- Rutas de viaje con vuelos, barcos, zepelines y el Tranvía Subterráneo, desde donde estás.
- Ayuda de clase según las guías actuales: builds de talentos, rotación, estadísticas, encantamientos y consejos para subir, además de profesiones, mazmorras, bandas y JcJ.
- Conoce a tu personaje: tus talentos y puntos sin gastar, profesiones, equipo y estadísticas, así que puedes preguntar «revisa mis talentos» o «¿dónde gasto el siguiente punto?».
- Recuerda la conversación, así que puedes seguir preguntando («¿y desde aquí?»).
- Desplázate por la conversación con la rueda del ratón o los botones de flecha; cambia el tamaño de la ventana del addon desde la esquina inferior derecha.
- Dice «no lo sé» en lugar de inventar. Inglés y español.
- Sin AskForever App, **Copiar prompt** copia la pregunta con tu contexto para pegarla en cualquier IA.
- Los datos del juego y las fichas llegan con las actualizaciones del addon desde CurseForge.

## Cómo se instala (unos 10 minutos, una vez)
1. Instala este addon.
2. Instala **AskForever App** para Windows desde la [última versión de GitHub](https://github.com/warcrafted-server/AskForever/releases/latest).
3. Abre AskForever App. La primera vez, su diálogo **Configurar IA** te ayuda a conseguir una clave gratuita de Google Gemini, la prueba y la guarda cifrada en el Administrador de credenciales de Windows.
4. Mantén AskForever App en marcha mientras juegas. Al cerrar su ventana, queda en la bandeja del sistema; para salir, usa el menú de la bandeja.
5. AskForever App se actualiza sola. Para actualizar los datos y las fichas, actualiza el addon en CurseForge; cuando hace falta, la app descarga desde GitHub una base de datos comprobada.

La primera vez que entras al juego, una ventana de bienvenida muestra estos pasos con los enlaces; `/af help` o el botón **?** la vuelven a abrir. La carpeta del addon incluye también la guía de instalación y el informe de seguridad y transparencia (`docs/`).

Guía paso a paso con capturas: [guía de instalación](https://github.com/warcrafted-server/AskForever/blob/main/docs/GUIA_INSTALACION.md).

## Privacidad y seguridad
- No lee la memoria del juego ni automatiza nada: no pulsa teclas ni mueve el ratón.
- Contacta con el proveedor de IA configurado y con la wiki cuando hace falta. GitHub comprueba versiones de la app y los datos y descarga el instalador o la base de datos; ambas descargas se verifican con SHA-256.
- Con cada pregunta, el addon envía a la IA un resumen de tu personaje (nivel, clase, zona, talentos, profesiones, equipo y estadísticas). No se envía nada que te identifique: ni nombre, ni reino, ni oro.
- AskForever App lee la carpeta de datos del addon sin modificarla. La clave se guarda cifrada en el Administrador de credenciales de Windows, nunca en un archivo de texto.
- AskForever App se compila en GitHub desde el código público, con hashes SHA-256 y prueba de procedencia. Windows puede mostrar un aviso la primera vez porque el programa no está firmado digitalmente: consulta [seguridad y transparencia](https://github.com/warcrafted-server/AskForever/blob/main/docs/SEGURIDAD_TRANSPARENCIA.md).

## Limitaciones de la beta
- AskForever App dibuja la respuesta sobre la ventana del addon, así que se oculta mientras el juego está minimizado o en segundo plano.

Las respuestas de la IA pueden contener errores: comprueba lo importante en el juego.

*World of Warcraft is a trademark of Blizzard Entertainment, Inc. Not affiliated with Blizzard. / World of Warcraft es una marca de Blizzard Entertainment, Inc. Sin afiliación con Blizzard.*
