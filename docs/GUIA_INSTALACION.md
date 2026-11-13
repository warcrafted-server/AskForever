# Guía de instalación de AskForever (ES)

**[English version](INSTALL_GUIDE.md)**

> 🚧 Guía viva: se actualiza con cada release. Si algún paso no coincide con lo que ves, revisa la última versión en GitHub.

Tiempo estimado: **5–10 minutos**, una sola vez. Después, solo abres el juego y preguntas.

---

## Índice
1. [Requisitos](#1-requisitos)
2. [Conseguir tu clave gratuita de Google Gemini](#2-conseguir-tu-clave-gratuita-de-google-gemini)
3. [Instalar el addon](#3-instalar-el-addon)
4. [Instalar el companion](#4-instalar-el-companion)
5. [Asistente de primera ejecución](#5-asistente-de-primera-ejecución)
6. [Reiniciar WoW (solo la primera vez)](#6-reiniciar-wow-solo-la-primera-vez)
7. [Primera pregunta](#7-primera-pregunta)
8. [Otros motores de IA (opcional)](#8-otros-motores-de-ia-opcional)
9. [Solución de problemas](#9-solución-de-problemas)
10. [Desinstalar](#10-desinstalar)
11. [Preguntas frecuentes](#11-preguntas-frecuentes)

---

## 1. Requisitos

- Windows 10 u 11.
- WoW Forever instalado.
- Una cuenta de Google (para la clave gratuita de IA).
- El juego en modo **"Ventana"** o **"Ventana (sin bordes)"**. En **pantalla completa exclusiva** el companion no puede leer la pantalla.
  - En el juego: `Esc` → **Opciones** → **Gráficos** → **Modo de visualización** → *Ventana (sin bordes)*.

## 2. Conseguir tu clave gratuita de Google Gemini

La clave es como una contraseña que permite al companion usar la IA de Google. **Es gratis y no pide tarjeta.**

1. Entra en **[Google AI Studio](https://aistudio.google.com/)** e inicia sesión con tu cuenta de Google.
2. Si es la primera vez, acepta los términos de uso.
3. En el menú de la izquierda, pulsa **Get API key** (Obtener clave de API).
4. Pulsa **Create API key** (Crear clave de API). Si te pide un proyecto, deja el que propone o crea uno nuevo.
5. Copia la clave (empieza por `AIza…`) con el botón de copiar.
6. Guárdala de momento en un lugar seguro: la pegarás en el paso 5.

![Crear clave en Google AI Studio](img/guide-aistudio-key.png) <!-- TODO captura -->

**Importante:**
- 🔒 **No compartas tu clave con nadie** ni la publiques. AskForever la guarda cifrada en el Administrador de credenciales de Windows.
- 🆓 El plan gratuito tiene **límites por minuto y por día**. Para un jugador normal sobra; si los superas, AskForever te avisará y podrás volver a preguntar en un momento.
- 📄 En el plan gratuito, Google puede usar el contenido de las consultas para mejorar sus productos (según su región y condiciones). No escribas datos personales en tus preguntas.
- Si algún día quieres más límite, puedes activar facturación en Google, pero **no es necesario**.

## 3. Instalar el addon

### Opción A: aplicación de CurseForge (recomendada)
1. Abre la app de **CurseForge** → **World of Warcraft**.
2. Comprueba que está seleccionada la instalación **Forever**. Si no aparece, usa *Scan for games* o añade manualmente la carpeta `World of Warcraft\_forever_`.
3. Busca **AskForever** y pulsa **Install**.

### Opción B: manual
1. Descarga el `.zip` desde la página de AskForever en CurseForge (pestaña **Files**, archivo marcado como *Forever*).
2. Descomprímelo y copia la carpeta `AskForever` en:
   `World of Warcraft\_forever_\Interface\AddOns\`
3. Debe quedar así: `...\AddOns\AskForever\AskForever.toc`

## 4. Instalar el companion

El companion es el programa que conecta el addon con la IA. Sin él, AskForever solo puede generar el prompt para copiarlo.

1. Ve a **[GitHub Releases de AskForever](https://github.com/warcrafted-server/AskForever/releases)**.
2. Descarga el último **`AskForever-Setup.exe`**.
3. Ejecútalo y sigue el instalador.
   - Si Windows muestra **"Windows protegió su PC"** (SmartScreen), pulsa **Más información** → **Ejecutar de todas formas**. Ocurre con programas nuevos de autores pequeños.

![Instalador del companion](img/guide-setup.png) <!-- TODO captura -->

## 5. Asistente de primera ejecución

Al terminar la instalación se abre el asistente:

1. **Carpeta de WoW**: detecta `_forever_` automáticamente. Si no la encuentra, pulsa *Buscar* y elige la carpeta `World of Warcraft\_forever_`.
2. **Motor de IA**: deja **Google Gemini (gratis)**.
3. **Clave**: pega la clave del paso 2 y pulsa **Probar**. Debe aparecer ✅.
4. **Preparar el addon**: el asistente crea los archivos auxiliares que necesita el addon para recibir respuestas (carpetas `AskForever_Slot…`). No las borres.
5. **Arranque automático**: déjalo activado para no tener que abrir el companion a mano.

El companion queda en la **bandeja del sistema** (junto al reloj).

![Asistente del companion](img/guide-wizard.png) <!-- TODO captura -->

## 6. Reiniciar WoW (solo la primera vez)

Si el juego estaba abierto, **ciérralo del todo y vuelve a abrirlo**. Un `/reload` no basta: el juego solo detecta addons nuevos al arrancar.

En la pantalla de selección de personaje, pulsa **AddOns** y comprueba que **AskForever** está activado.

## 7. Primera pregunta

1. Entra con tu personaje.
2. Escribe `/af test` en el chat. Debe responder **"✅ Conexión correcta"**. Si no, ve a [Solución de problemas](#9-solución-de-problemas).
3. Abre AskForever con `/af` o con el atajo de teclado (configurable en *Opciones → Atajos → AskForever*).
4. Escribe tu pregunta, por ejemplo: *¿por dónde voy a Baldíos?*
5. En unos segundos verás la respuesta. Pulsa **Llévame** para poner los puntos en el mapa y la flecha.

No hace falta decir tu nivel, facción ni dónde estás: AskForever lo sabe.

![Primera pregunta](img/guide-first-question.png) <!-- TODO captura -->

## 8. Otros motores de IA (opcional)

En el companion: clic derecho en el icono de la bandeja → **Ajustes** → **Motor de IA**.

| Motor | Coste | Qué necesitas |
|---|---|---|
| **Google Gemini** (por defecto) | Gratis | Clave de [AI Studio](https://aistudio.google.com/) |
| **API compatible con OpenAI** (OpenCode, OpenRouter…) | Según proveedor | URL base, clave y nombre del modelo |
| **Claude** | De pago por uso | Clave de API de [Claude Console](https://console.anthropic.com/) (no sirve la suscripción Pro de claude.ai) |
| **Ollama** (local) | Gratis | [Ollama](https://ollama.com/) instalado y un modelo descargado; recomendable una GPU con 8 GB o más |

## 9. Solución de problemas

| Problema | Solución |
|---|---|
| `/af` no hace nada | AskForever no está activado o no reiniciaste WoW. Revisa el paso 6. |
| `/af test` dice "Companion no detectado" | Abre el companion (icono en la bandeja). Comprueba que el juego no está en pantalla completa exclusiva. |
| La respuesta aparece en una ventana encima del juego y no en el addon | Se agotaron los archivos de respuesta o fallaron. Haz `/reload` o vuelve a ejecutar *Preparar el addon* en el companion. |
| "Límite de uso alcanzado" | Has superado el límite gratuito de Google. Espera un minuto (o al día siguiente si es el límite diario). |
| "Clave no válida" | Vuelve a copiar la clave en AI Studio y pégala en *Ajustes*. |
| No responde dentro de mazmorras o en combate | Es intencionado: la pregunta se guarda y se envía al salir del combate o de la instancia. |
| La tira de colores de la esquina molesta | Solo aparece unos instantes mientras se envía la pregunta. |

Si el problema sigue, abre una incidencia en [GitHub Issues](https://github.com/warcrafted-server/AskForever/issues) con el resultado de `/af test`.

## 10. Desinstalar

1. Companion: *Configuración de Windows → Aplicaciones → AskForever → Desinstalar*. Ofrece borrar también las carpetas `AskForever_Slot…`.
2. Addon: desinstálalo en CurseForge o borra la carpeta `Interface\AddOns\AskForever`.
3. Si quieres, borra tu clave en [AI Studio](https://aistudio.google.com/).

## 11. Preguntas frecuentes

**¿Es gratis?** Sí, el addon y el companion son gratuitos. Con Gemini, la IA también.

**¿Me pueden banear?** AskForever no simula teclas, no lee la memoria del juego ni automatiza acciones: solo muestra información. Aun así, Blizzard no se ha pronunciado sobre este tipo de programas, así que no podemos garantizar nada. Úsalo bajo tu responsabilidad.

**¿Qué datos envía?** Tu pregunta y el contexto del personaje (nivel, clase, facción, zona, coordenadas, misiones). Nada de tu cuenta ni contraseñas.

**¿Funciona en Mac o Linux?** De momento solo Windows.
