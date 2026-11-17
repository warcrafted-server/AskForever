# TODO

El detalle de cada hito está en [ROADMAP.md](ROADMAP.md). Lo hecho está en el [CHANGELOG](CHANGELOG.md).

## Alta
- **Publicar la 0.3.0-beta.1 en CurseForge** (Marc): subir el zip de la release de GitHub como «Beta 3» y actualizar resumen y descripción (textos en `docs/CURSEFORGE.md`). Después, añadir el enlace del proyecto de CurseForge al README y a las guías.
- **VirusTotal**: analizar `AskForever-Setup-0.3.0-beta.1.exe` y enlazar el informe en la release y en la página de transparencia (hoy figura como «Previsto»).
- **Actualizaciones de datos por CurseForge**: parche acumulado en texto plano dentro del addon (`data/`), lector y aplicador en el companion (siempre base limpia + parche; base exacta desde GitHub si hace falta), script que genera el parche desde wowdata. Diseño en `.agents/plans/publico/publico.PLAN.md`.
- **Guía de principiantes**: índice de temas hecho (`.agents/plans/guia/indice.md`); siguientes pasos: paquete de pruebas por tema desde wowdata, redacción con citas, verificación guiada y lectura desde el companion. Plan en `.agents/plans/guia/guia.PLAN.md`. Repetir el diagnóstico del colector (`/wdc probe`) con un personaje de nivel 10 o más para ver los talentos.
- **Créditos de los datos** (Blizzard y Wowhead) cuando wowdata deje de incluir Questie: `CREDITS.md` EN/ES con la Skill `licencias` y autorización de Marc.

- **Leer respuestas largas en el chat** (pedido por Marc): ventana del addon redimensionable, desplazamiento con la rueda y botones ▲/▼ sobre el panel (el overlay no recibe clics), y mostrar cada respuesta nueva desde su principio. Diseño en `.agents/plans/consultas/consultas.PLAN.md` (3c).

## Media
- **Chat dentro de la ventana del addon** (vuelta por addons «slot»): diseño en `.agents/plans/m3-slots/m3-slots.PLAN.md`; con ello, la ventana de informe podrá mostrar la respuesta.
- **Perfil completo del personaje**: profesiones, talentos, equipo, reputaciones…; primero verificar en el cliente qué API existe; a la IA solo lo relevante para la pregunta.
- **Gemma 4 por Cloudflare Workers AI como proveedor opcional** (Gemini Flash-Lite sigue por defecto, decisión de Marc 2026-11-17): proveedor `cloudflare` que pida también el ID de cuenta, sin razonamiento del modelo, y sección en las guías ES/EN (cuenta, token, ID, límite de ~70 preguntas/día). Resultados y detalles en `.agents/plans/consultas/consultas.PLAN.md`.
- **Puntos de talento por nivel**: con los puntos en el contexto, la IA sigue dando más de los que hay («qué talentos debería tener a nivel 34»); calcular en el companion la parte de la ruta que corresponde al nivel.
- Elegir y recordar el proveedor de IA desde el asistente del companion (hoy solo Gemini; los demás por variable de entorno).
- Probar otras resoluciones y escalas de interfaz de la tira de píxeles (probado: 1920x1080, ventana sin bordes).
- Validar en el juego el atajo de teclado (Opciones → Atajos → AddOns) tal como lo describen las guías.
- Instalar `luacheck` si el volumen de errores lo justifica.
- **Automatizar el análisis de VirusTotal del instalador** en el workflow de Release (API de VirusTotal, clave en los secrets de GitHub) y actualizar la insignia del README automáticamente; mientras tanto, la insignia y los enlaces se actualizan a mano en cada release.

## Baja
- «Llévame»: pines y flecha en el mapa.
- Autoactualización del companion.
- Microsoft Store, PyPI o winget, si el proyecto tiene buena acogida (aparcado por decisión de Marc, 2026-11-14).
- Lanzamiento estable v1.0.0.

## Descartado
- Simular input, leer memoria del proceso o inyectar overlays: vulnera las reglas del juego y arriesga baneos.
- Firmar el `.exe` con certificado de pago para quitar el aviso de SmartScreen: desde 2024 no evita el aviso de entrada; Azure Artifact Signing no admite particulares de España; SignPath exige licencia OSI.
- Construir la base de datos en el PC del jugador desde su cliente y su Questie: demasiado complejo (decisión de Marc, 2026-11-14).
- Usar `gemini-3.8-flash` (o 3.5/3.6/3.7 Flash sin «Lite») como modelo por defecto: en el plan gratuito devuelven 503 (2026-11-14 y 2026-11-17); revisar más adelante.
- Otros modelos gratuitos probados el 2026-11-17 (Nemotron 3 Ultra y 120B, GLM 4.7 Flash, ERNIE 5.5, Inkling 2, Qwen3 30B, Kimi K2.5): o inventan más que Gemini, o tienen muy pocas peticiones al día, o no están disponibles gratis.
