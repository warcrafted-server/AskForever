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
   - **Changelog:** the file `curseforge/changelog-<version>.md` (bilingual, written for players): open it, Ctrl+A, copy and paste it with the **Markdown** format selected.
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

### Description (English and Spanish)

Open [`curseforge/description.md`](curseforge/description.md), select everything (Ctrl+A), copy and paste it into the description editor in **Markdown** mode. Do not copy it from this page.

### File changelogs (paste in the upload form)

Each version has its own file in [`curseforge/`](curseforge/): open it, Ctrl+A, copy and paste it into the changelog box with the **Markdown** format selected.

#### 0.3.0-beta.3 (Beta 4)

[`curseforge/changelog-0.3.0-beta.3.md`](curseforge/changelog-0.3.0-beta.3.md)

#### 0.3.0-beta.2 (Beta 3)

[`curseforge/changelog-0.3.0-beta.2.md`](curseforge/changelog-0.3.0-beta.2.md)

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
   - **Registro de cambios:** el archivo `curseforge/changelog-<versión>.md` (bilingüe): ábrelo, Ctrl+A, cópialo y pégalo con el formato **Markdown** elegido. No lo copies desde esta página.
4. Si cambian las funciones, actualiza el **resumen** y la **descripción** (`curseforge/description.md`, bilingüe, en modo Markdown).

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
