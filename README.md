# AskForever

**[English](#english) · [Español](#español)**

> 🚧 Under development: no downloadable version yet. The first beta (v0.1.0) works in the game but is not published yet.
> En desarrollo: todavía no hay versión descargable. La primera beta (v0.1.0) ya funciona en el juego pero aún no está publicada.

---

## English

**AI assistant for WoW Forever.** Ask in plain language and get the answer in-game:

> *"How do I get from Westfall to The Barrens at a low level?"*

### Goal
AskForever knows your level, faction and zone, computes routes from real data (no guessing) and gives you a waypoint arrow.

### Status
| Version | What it brings | State |
|---|---|---|
| 0.1.0 | Addon: chat window, character context, **Copy prompt** button (paste it into any AI) | Working, not published yet |
| 0.2.0 – 0.4.0 | Companion app that talks to the AI and shows the answer in-game, installer | Planned |
| 0.5.0+ | Reliable routes, **Take me there** button, more AI engines | Planned |

See the [ROADMAP](ROADMAP.md), the [CHANGELOG](CHANGELOG.md) and the [TODO](TODO.md).

### Design principles
- **No simulated input and no memory reading.** The addon only uses the official addon API.
- WoW addons cannot access the Internet, so a small desktop **companion** (from v0.2.0) will bridge the addon and the AI.
- Planned AI engines: Google Gemini (free key), Ollama (local), or your own Claude / OpenAI-compatible API key.
- Languages: English and Spanish.

### Installation
👉 [Installation guide](docs/INSTALL_GUIDE.md)

### Disclaimer
AI answers may contain mistakes; double-check important details in game. Blizzard has no official position on desktop companions: AskForever is designed not to automate any gameplay action, but use it at your own risk.

---

## Español

**Asistente de IA para WoW Forever.** Pregunta en lenguaje natural y recibe la respuesta dentro del juego:

> *"¿Por dónde voy de Páramos de Poniente a Baldíos siendo nivel bajo?"*

### Objetivo
AskForever conoce tu nivel, facción y zona, calcula las rutas con datos reales (no inventa) y te pone una flecha al destino.

### Estado
| Versión | Qué aporta | Estado |
|---|---|---|
| 0.1.0 | Addon: ventana de chat, contexto del personaje, botón **Copiar prompt** (pégalo en cualquier IA) | Funciona, sin publicar |
| 0.2.0 – 0.4.0 | Companion que habla con la IA y muestra la respuesta en el juego, instalador | Planificado |
| 0.5.0+ | Rutas fiables, botón **Llévame**, más motores de IA | Planificado |

Consulta la [hoja de ruta](ROADMAP.md), el [CHANGELOG](CHANGELOG.md) y el [TODO](TODO.md).

### Principios de diseño
- **No simula teclas ni lee la memoria del juego.** El addon solo usa la API oficial de addons.
- Los addons de WoW no pueden acceder a Internet, así que un pequeño **companion** de escritorio (desde la v0.2.0) conectará el addon con la IA.
- Motores de IA previstos: Google Gemini (clave gratuita), Ollama (local) o tu propia clave de Claude / API compatible con OpenAI.
- Idiomas: inglés y español.

### Instalación
👉 [Guía de instalación](docs/GUIA_INSTALACION.md)

### Aviso
Las respuestas de IA pueden contener errores; verifica lo importante en el juego. Blizzard no tiene una postura oficial sobre programas de escritorio: AskForever está diseñado para no automatizar ninguna acción de juego, pero úsalo bajo tu responsabilidad.

---

**Author / Autor:** WarCrafted · warcrafted.server@gmail.com
**License / Licencia:** [CC BY-NC 4.0](LICENSE) · World of Warcraft is a trademark of Blizzard Entertainment, Inc. Not affiliated with Blizzard.
