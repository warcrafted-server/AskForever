# TODO

El detalle de cada milestone está en [ROADMAP.md](ROADMAP.md).

## Alta
- Publicar la v0.2.0-beta.1 cuando Marc lo decida (el companion todavía no va en el paquete de CurseForge): push, tag y release en GitHub con su aprobación.
- **Memoria de conversación**: que recuerde las últimas preguntas de la sesión (historial en el companion, caducidad por tiempo).
- **Comparar modelos de verdad**: guardar claves de Groq, Mistral, Cerebras y OpenRouter (`set-key --provider NOMBRE`, `providers`, `list-models`), lanzar `bench` con varios objetivos, puntuar a mano el informe y decidir qué servicios recomendar. Línea base Gemini (gemini-3.5-flash-lite): 10/10 respondidas, mediana 742 ms; falló responder en inglés (q10), inventó rutas (q03) y niveles de mazmorras (q06); acertó las preguntas trampa (q08, q09).
- **Chat dentro de la ventana del addon** (milestone 3, retorno por addons «slot»): escribir y que la respuesta salga en el historial como un chat; el overlay queda como respaldo.
- **Perfil completo del personaje**: profesiones y niveles, talentos y rama, equipo y bolsas, hechizos y habilidades de armas, reputaciones, etc. Primero verificar en el cliente qué API existe (volcado a SavedVariables); el companion guarda el perfil y a la IA solo se le envía lo relevante para la pregunta (decisión de Marc, 2026-11-14).
- Calidad de las respuestas: datos fiables de Forever (grafo de rutas, guías) en lugar de depender del conocimiento general del modelo (milestone 5).

## Media
- Milestones 4–7 del roadmap (instalador, rutas, robustez, multi-proveedor).
- Probar otras resoluciones y escalas de interfaz de la tira de píxeles (probado: 1920x1080, ventana sin bordes).
- Instalar `luacheck` si el volumen de errores lo justifica (el ejecutable externo se denegó).
- Validar en el juego el atajo de teclado (Opciones → Atajos → AddOns) tal como lo describen las guías.

## Baja
- Contenido (misiones, NPCs, RAG de guías) y lanzamiento estable v1.0.0.

## Descartado
- Simular input, leer memoria del proceso o inyectar overlays: vulnera las reglas del juego y arriesga baneos.
- Usar `gemini-3.8-flash` como modelo por defecto: no respondió en 60 s en el plan gratuito (2026-11-14); revisar más adelante.
