# TODO

El detalle de cada hito está en [ROADMAP.md](ROADMAP.md). Lo hecho está en el [CHANGELOG](CHANGELOG.md).

## Alta
- **Dónde comprar bolsas baratas de N casillas** (Marc, 2026-11-24, informe 171314-437): la IA contesta «no tengo ese dato» porque el motor no tiene herramienta de objetos en vendedor. wowdata ya trae `v_vendedor_objeto` (precio y vendedor) y las casillas de bolsa salen de `ItemSparse`; falta una herramienta determinista (bolsas por casillas, precio más bajo, vendedor cercano al jugador) y enrutarla. Diseño Opus, implementación AgentRelay.
- **El companion debe usar las vistas con prioridad de wowdata** (2026-11-24): hoy lee las tablas `ext_*` de Questie (la fuente de menos prioridad) y no usa pesca, instructores de profesión, vendedores ni eventos. Plan en `.agents/plans/vistas-wowdata/vistas-wowdata.PLAN.md`.
- **Próxima actualización: base de datos nueva** (Marc, 2026-11-24): el parche 2026.11.24.2 pesa 11,8 MB porque se compara con `data-2026.11.18` (sobre todo `questie_spawn`). Publicar una base `data-…` desde el `wow.sqlite` actual de wowdata y generar los parches contra ella para que vuelvan a ser pequeños.
- **Publicar la 0.3.0-beta.1 en CurseForge** (Marc): subir el zip de la release de GitHub como «Beta 3» y actualizar resumen y descripción (textos en `docs/CURSEFORGE.md`). Después, añadir el enlace del proyecto de CurseForge al README y a las guías.
- **VirusTotal** (SecureAge, falso positivo de la 0.3.0-beta.3): SecureAPlus respondió que lo retirará en 72 horas desde su respuesta (envío 20261115-023523737900); si no desaparece, escribir a secureaplus@secureage.com. Cuando se retire: volver a analizar el instalador, comprobar que no hay detecciones y actualizar la insignia del README, la página de transparencia (`SECURITY_TRANSPARENCY.md` y `SEGURIDAD_TRANSPARENCIA.md`) y el enlace del informe, con un análisis de la beta.12 en lugar de la beta.3.
- **Actualizaciones de datos por CurseForge**: parche acumulado en texto plano dentro del addon (`data/`), lector y aplicador en el companion (siempre base limpia + parche; base exacta desde GitHub si hace falta), script que genera el parche desde wowdata. Diseño en `.agents/plans/publico/publico.PLAN.md`.
- **Guía de principiantes**: índice de temas hecho (`.agents/plans/guia/indice.md`); siguientes pasos: paquete de pruebas por tema desde wowdata, redacción con citas, verificación guiada y lectura desde el companion. Plan en `.agents/plans/guia/guia.PLAN.md`. Repetir el diagnóstico del colector (`/wdc probe`) con un personaje de nivel 10 o más para ver los talentos.
- **Créditos de los datos** (Blizzard y Wowhead) cuando wowdata deje de incluir Questie: `CREDITS.md` EN/ES con la Skill `licencias` y autorización de Marc.

- **Leer respuestas largas en el chat** (pedido por Marc): ventana del addon redimensionable, desplazamiento con la rueda y botones ▲/▼ sobre el panel (el overlay no recibe clics), y mostrar cada respuesta nueva desde su principio. Diseño en `.agents/plans/consultas/consultas.PLAN.md` (3c).
- **Paquete de Linux compilado en GitHub** (0.5.0-beta.1): el trabajo de Linux del workflow Release se ejecutó bien y el tar.gz está en la release; falta comprobar que ese paquete, compilado en Ubuntu, funciona en Arch.
- **Capturas purgadas del historial (2026-11-25): pendiente GitHub** (Marc): los commits antiguos pueden seguir accesibles por su identificador hasta que el soporte de GitHub los limpie; pedirlo en https://support.github.com (commit `e84ce60` y la antigua etiqueta v0.4.0-beta.12).

## Media
- **Druida Equilibrio: Wowhead y los datos del juego no coinciden** (2026-11-25, build 71139): el calculador de Wowhead muestra «Starlight Wrath», «Moon and Stars», «Dreamstate» en el sitio de «Moonfury» e «Improved Starfire» con 2 rangos; las DB2 no lo confirman y mandan ellas, así que las fichas no se tocan. Volver a comprobarlo con la próxima actualización. Afecta a los paquetes descodificados y a `ext_wh_*`.
- **Guías nuevas sin ficha** (2026-11-25): guías de subida 1-60 de Mago y de Brujo y conjuntos de mazmorra de nivel 0.5 (Tier 0.5).
- **Descripción de los objetos en las respuestas** (wowdata, 2026-11-24): el companion no lee la descripción del objeto (`ItemSparse.Description_lang_esES`, con el inglés de respaldo; 4820 de 4828 la tienen en español). Añadirla a `item_sources` ayudaría con «¿qué hago con este objeto?»; hoy esa pregunta solo se salva si hay ficha.
- **Actualización diaria de guías** (Marc, 2026-11-18): `companion/tools/guide_update.py` que importe la descarga del día, refresque solas las fichas con cambios solo de forma y prepare tareas estrechas por clase. Plan en `.agents/plans/actualizacion-diaria/`.
- **Chat dentro de la ventana del addon** (vuelta por addons «slot»): diseño en `.agents/plans/m3-slots/m3-slots.PLAN.md`; con ello, la ventana de informe podrá mostrar la respuesta.
- **Perfil completo del personaje**: profesiones, talentos, equipo, reputaciones…; primero verificar en el cliente qué API existe; a la IA solo lo relevante para la pregunta.
- **Gemma 4 por Cloudflare Workers AI como proveedor opcional** (Gemini Flash-Lite sigue por defecto, decisión de Marc 2026-11-17): proveedor `cloudflare` que pida también el ID de cuenta, sin razonamiento del modelo, y sección en las guías ES/EN (cuenta, token, ID, límite de ~70 preguntas/día). Resultados y detalles en `.agents/plans/consultas/consultas.PLAN.md`.
- **Publicar las bases de datos sin pasos a mano** (Marc, 2026-11-18): hoy la release `data-…` se sube desde la web porque las claves SSH no sirven para la API de releases. Estudiar un workflow que genere y publique la base con el token de Actions (necesita acceso a la base de wowdata) o que la publique wowdata.
- Elegir y recordar el proveedor de IA desde el asistente del companion (hoy solo Gemini; los demás por variable de entorno).
- Probar otras resoluciones y escalas de interfaz de la tira de píxeles (probado: 1920x1080, ventana sin bordes).
- Validar en el juego el atajo de teclado (Opciones → Atajos → AddOns) tal como lo describen las guías.
- Instalar `luacheck` si el volumen de errores lo justifica.
- **Automatizar el análisis de VirusTotal del instalador** en el workflow de Release (API de VirusTotal, clave en los secrets de GitHub) y actualizar la insignia del README automáticamente; mientras tanto, la insignia y los enlaces se actualizan a mano en cada release.
- **Análisis de VirusTotal del paquete de Linux** (0.5.0-beta.1): analizar el `.tar.gz` y enlazar el informe en las notas de la versión y en las páginas de transparencia.
- **Ocultar el overlay al cambiar de ventana con WoW en Wayland nativo**: con Wine/Proton en Wayland nativo el panel sigue visible al pasar a otra ventana.
- **Probar Linux más allá de lo verificado**: GNOME, otras distribuciones, WoW con XWayland dentro del juego, sesiones X11 y varios monitores con el juego fuera del monitor izquierdo.

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
