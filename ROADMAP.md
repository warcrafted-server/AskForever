# AskForever — Roadmap / Hoja de ruta

Desarrollo continuo con **una release beta al día**. Cada milestone es publicable por sí mismo.
Si un milestone no cabe en el día, se publica la parte estable y el resto pasa al siguiente.

Leyenda: ⬜ pendiente · 🟨 en curso · ✅ publicado

---

## ⬜ v0.1.0-beta — Día 1 · Addon base + "Copiar prompt"
Primera release útil **sin companion**.
- Ventana de chat (estilo Lorewake), `/askforever` y `/af`, atajo de teclado configurable.
- Recogida de contexto: nivel, raza, clase, facción, zona, subzona, coordenadas, misiones activas.
- Botón **"Copiar prompt"**: EditBox con el prompt + contexto seleccionado (Ctrl+C) para pegar en
  cualquier IA.
- Locales `esES`/`esMX` y `enUS`. Botón de minimapa.
- **Criterios**: carga sin errores en Forever (BugSack limpio); el prompt incluye el contexto correcto.
- **Capturas**: ventana abierta · prompt generado · botón de minimapa.

## ⬜ v0.2.0-beta — Día 2 · Prueba de transporte (ida) + respuesta en overlay
- Addon: tira de píxeles (cabecera, longitud, secuencia, CRC32), visible solo con mensaje pendiente.
- Companion (CLI): captura de la región, decodificación, ACK, llamada a **Gemini**
  (`gemini-3.8-flash`, endpoint OpenAI-compatible) y respuesta en **ventana overlay**.
- Guardado de la API key con `keyring`.
- **Criterios**: 20 preguntas seguidas sin pérdidas; latencia de ida < 1 s; error 429 gestionado.
- ⚠️ **Punto de decisión**: si la captura no funciona en Forever, se replantea el plan aquí.
- **Capturas**: tira en pantalla · overlay con respuesta.

## ⬜ v0.3.0-beta — Día 3 · Respuesta dentro del juego (vuelta por slots LoD)
- Companion: `askforever dev-setup` genera el pool `AskForever_SlotNNN`; escribe respuestas en slots libres.
- Addon: sondeo, `C_AddOns.LoadAddOn`, render en la ventana y en el chat. Reciclado en login/carga.
- Fallback automático a overlay si no hay slots.
- **Criterios**: respuesta visible en el juego sin `/reload`; total 3–10 s.
- **Capturas**: pregunta y respuesta dentro de la ventana del addon.

## ⬜ v0.4.0-beta — Día 4 · Instalador y asistente de primera ejecución
- `.exe` (PyInstaller): detecta `_forever_`, pide la API key (abre AI Studio), la prueba,
  genera slots, se añade al arranque, icono en bandeja.
- `/af test`: autodiagnóstico de extremo a extremo con mensajes claros.
- **Criterios**: instalación limpia en un Windows sin Python en < 5 minutos.
- **Capturas**: cada pantalla del asistente · resultado de `/af test`.

## ⬜ v0.5.0-beta — Día 5 · Rutas fiables + "Llévame"
- `data/routes.json`: grafo de zonas (rangos de nivel, facción, barcos, zepelines, a pie, vuelos).
- Motor: router de intención → Dijkstra con penalización por nivel/facción → LLM redacta.
- Addon: botón **"Llévame"**: pines en el mapa y flecha.
- **Criterios**: 30 preguntas de rutas de prueba correctas para ambas facciones.
- **Capturas**: respuesta de ruta · pines en el mapa · flecha.

## ⬜ v0.6.0-beta — Día 6 · Conversación natural y robustez
- Memoria de conversación (seguimientos: "¿y es peligroso?").
- Cola en combate / bloqueo de chat en instancias; envío al salir.
- Respuestas con fuente y nivel de confianza; modo "no lo sé".

## ⬜ v0.7.0-beta — Día 7 · Multi-proveedor
- Selector en el companion: Gemini (gratis) · OpenCode / OpenAI-compatible · Claude (API key) · Ollama.
- Pruebas finales con la API de OpenCode.

## ⬜ v0.8.0+ — Contenido
- Misiones, NPCs, farmeo y profesiones (datos compartidos con Farm Advisor). RAG de guías.

## ⬜ v1.0.0 — Lanzamiento estable
- Guías ES/EN completas con capturas, página de CurseForge final, vídeo corto de demo.
