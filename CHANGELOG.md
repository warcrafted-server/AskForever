# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/). Versioning: [SemVer](https://semver.org/). English first, then Spanish / Inglés primero, después español.

## [Unreleased]

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
