# CurseForge — publication kit / Kit de publicación

> ⚠️ **Do not paste this page into CurseForge. / No pegues esta página en CurseForge.**
> Public description / Descripción pública: [`curseforge/description.md`](curseforge/description.md) · Changelogs / Registros de cambios: [`curseforge/`](curseforge/)

**[English](#english) · [Español](#español)**

Since 0.3.0-beta.4 the file upload is **automatic**: the Release workflow uploads the addon zip when a `v<version>` tag is pushed, with `curseforge/changelog-<version>.md` as changelog (Markdown) and its "Beta N" as display name. The description and project fields are still edited by hand.
Desde la 0.3.0-beta.4 la subida del archivo es **automática**: el workflow Release sube el zip del addon al subir el tag `v<versión>`, con `curseforge/changelog-<versión>.md` como registro de cambios (Markdown) y su «Beta N» como nombre visible. La descripción y los campos del proyecto se siguen editando a mano.

Current version / Versión actual: **0.5.0-beta.2 (Beta 19)**, 2026-11-26. The 0.3.0-beta.1 was never uploaded to CurseForge; Beta 3 includes it. / La 0.3.0-beta.1 no se subió a CurseForge; la Beta 3 la incluye.

---

## English

### Every new version (update)
The CurseForge project already exists: a new version is just a **file upload** to it, and the Release workflow does it by itself (steps 2 and 3 below are only for uploading by hand if it fails or the `CF_API_KEY` secret is missing; with no key the workflow only warns and uploads nothing, so check the Files tab after each release).

1. The GitHub release is created by the release workflow when the `v<version>` tag is pushed (installer, addon zip, SHA-256 hashes and build provenance). Nothing is built locally.
2. Download the addon zip from that release: `https://github.com/warcrafted-server/AskForever/releases/download/v<version>/AskForever-<version>.zip`
3. On CurseForge: **Files → Upload File**.
   - **File:** the zip from step 2.
   - **Display name:** `AskForever <version> (Beta N)`, where N counts the betas published on CurseForge (0.3.0-beta.2 is Beta 3, 0.3.0-beta.3 is Beta 4, 0.3.0-beta.4 is Beta 5; 0.4.0-beta.N is Beta N+5, so 0.4.0-beta.12 is Beta 17; 0.5.0-beta.N is Beta N+17, so 0.5.0-beta.2 is Beta 19). The version number must stay exactly as in the addon and GitHub, so players can report which one they have.
   - **Release type:** Release (the workflow always uploads it as Release because betas reach very few players on CurseForge; Marc, 2026-11-18).
   - **Game version:** Forever.
   - **Changelog:** the file `curseforge/changelog-<version>.md` (bilingual, written for players): open it, Ctrl+A, copy and paste it with the **Markdown** format selected.
4. If the features changed, update the **summary** and the **description** with the texts below.

### Project fields (set once; review when features change)
| Field | Value |
|---|---|
| Name | AskForever |
| Summary | Ask inside WoW Forever and get answers over the game with verified data. AskForever App connects the addon to AI; game data and guide cards update with the addon. |
| Author | WarCrafted |
| License | Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0); if it is not offered, "Custom" with the text of `LICENSE` |
| Source | https://github.com/warcrafted-server/AskForever |
| Issues | https://github.com/warcrafted-server/AskForever/issues |
| Logo | `docs/img/logo.png` (400x400) |
| Screenshots | `docs/img/v0.4.0-chat-consejos.png`, `docs/img/v0.4.0-chat-build.png`, `docs/img/v0.4.0-chat-misiones.png`, `docs/img/v0.4.0-app-ventana.png`, `docs/img/v0.3.0-install-first-run.png` |

In the description, link only to pages of the GitHub project (no direct download links).

### Description (English and Spanish)

Open [`curseforge/description.md`](curseforge/description.md), select everything (Ctrl+A), copy and paste it into the description editor in **Markdown** mode. Do not copy it from this page.

### File changelogs (paste in the upload form)

Each version has its own file in [`curseforge/`](curseforge/): open it, Ctrl+A, copy and paste it into the changelog box with the **Markdown** format selected.

#### 0.5.0-beta.2 (Beta 19)

[`curseforge/changelog-0.5.0-beta.2.md`](curseforge/changelog-0.5.0-beta.2.md)

#### 0.5.0-beta.1 (Beta 18)

[`curseforge/changelog-0.5.0-beta.1.md`](curseforge/changelog-0.5.0-beta.1.md)

#### 0.4.0-beta.12 (Beta 17)

[`curseforge/changelog-0.4.0-beta.12.md`](curseforge/changelog-0.4.0-beta.12.md)

The rest of the 0.4.0 betas (Beta 6 to Beta 16) have their own file in the same folder.

#### 0.3.0-beta.4 (Beta 5)

[`curseforge/changelog-0.3.0-beta.4.md`](curseforge/changelog-0.3.0-beta.4.md)

#### 0.3.0-beta.3 (Beta 4)

[`curseforge/changelog-0.3.0-beta.3.md`](curseforge/changelog-0.3.0-beta.3.md)

#### 0.3.0-beta.2 (Beta 3)

[`curseforge/changelog-0.3.0-beta.2.md`](curseforge/changelog-0.3.0-beta.2.md)

---

## Español

### Cada versión nueva (actualización)
El proyecto de CurseForge ya existe: una versión nueva es solo **subir un archivo** a él, y el workflow Release lo hace solo (los pasos 2 y 3 son solo para subirlo a mano si falla o si falta el secreto `CF_API_KEY`; sin clave el workflow solo avisa y no sube nada, así que mira la pestaña Files tras cada release).

1. La release de GitHub la crea el workflow de release al subir la etiqueta `v<versión>` (instalador, zip del addon, hashes SHA-256 y prueba de procedencia). No se compila nada en local.
2. Descarga el zip del addon de esa release: `https://github.com/warcrafted-server/AskForever/releases/download/v<versión>/AskForever-<versión>.zip`
3. En CurseForge: **Files → Upload File**.
   - **Archivo:** el zip del paso 2.
   - **Nombre visible:** `AskForever <versión> (Beta N)`, donde N cuenta las betas publicadas en CurseForge (la 0.3.0-beta.2 es la Beta 3, la 0.3.0-beta.3 la Beta 4 y la 0.3.0-beta.4 la Beta 5; la 0.4.0-beta.N es la Beta N+5, así que la 0.4.0-beta.12 es la Beta 17; la 0.5.0-beta.N es la Beta N+17, así que la 0.5.0-beta.2 es la Beta 19). El número de versión se mantiene exactamente igual que en el addon y en GitHub, para que los jugadores puedan decir cuál tienen.
   - **Tipo:** Release (el workflow siempre la sube como Release porque las betas llegan a muy poca gente en CurseForge; Marc, 2026-11-18).
   - **Versión del juego:** Forever.
   - **Registro de cambios:** el archivo `curseforge/changelog-<versión>.md` (bilingüe): ábrelo, Ctrl+A, cópialo y pégalo con el formato **Markdown** elegido. No lo copies desde esta página.
4. Si cambian las funciones, actualiza el **resumen** y la **descripción** (`curseforge/description.md`, bilingüe, en modo Markdown).

### Campos del proyecto (se ponen una vez; revisarlos cuando cambien las funciones)
| Campo | Valor |
|---|---|
| Nombre | AskForever |
| Resumen | Pregunta en WoW Forever y recibe respuestas sobre el juego con datos verificados. AskForever App conecta el addon con la IA; los datos y las fichas se actualizan con el addon. |
| Autor | WarCrafted |
| Licencia | Creative Commons Atribución-NoComercial 4.0 (CC BY-NC 4.0); si no aparece, «Custom» con el texto de `LICENSE` |
| Código | https://github.com/warcrafted-server/AskForever |
| Incidencias | https://github.com/warcrafted-server/AskForever/issues |
| Logo | `docs/img/logo.png` (400x400) |
| Capturas | `docs/img/v0.4.0-chat-consejos.png`, `docs/img/v0.4.0-chat-build.png`, `docs/img/v0.4.0-chat-misiones.png`, `docs/img/v0.4.0-app-ventana.png`, `docs/img/v0.3.0-install-first-run.png` |

En la descripción, enlaza solo a páginas del proyecto en GitHub (sin enlaces de descarga directa).
