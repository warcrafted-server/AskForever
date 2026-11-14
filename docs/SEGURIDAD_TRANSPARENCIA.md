# Seguridad y transparencia

*English version: [SECURITY_TRANSPARENCY.md](SECURITY_TRANSPARENCY.md)*

AskForever tiene dos partes: el **addon** (funciona dentro del juego, como cualquier otro
addon) y el **companion** (un pequeño programa de Windows que habla con la IA). Esta página
explica exactamente qué hace el companion y qué no hace nunca, para que decidas con todos los
datos. Todo lo que pone aquí se puede comprobar en el código fuente de este repositorio.

## En un minuto

- **Mira una pequeña franja de la ventana del juego** (512 × 32 píxeles en la esquina
  superior izquierda), donde el addon dibuja tu pregunta con píxeles de colores. Nada más de
  tu pantalla.
- Envía tu pregunta y algo de contexto del personaje al **proveedor de IA que tú elijas**, y
  puede consultar **warcraft.wiki.gg**. No se conecta a nada más.
- **Nunca** lee la memoria del juego, no inyecta nada en el juego y no pulsa teclas ni mueve
  el ratón por ti.
- Tu clave de la API se guarda en el **Administrador de credenciales de Windows**, nunca en un
  archivo de texto.
- Sin cuentas, sin telemetría y sin servidores propios: no existe ningún servidor de
  AskForever.

## Qué hace el companion

| Qué | Detalle | Dónde está en el código |
|---|---|---|
| Encuentra la ventana del juego | Recorre las ventanas visibles y comprueba cuál es de `Wow.exe` (solo pide a Windows el nombre del proceso, con el permiso mínimo `PROCESS_QUERY_LIMITED_INFORMATION`). | `companion/askforever/capture/window.py` |
| Lee la tira de píxeles | Captura solo una zona de 512 × 32 píxeles de la esquina superior izquierda de la ventana del juego, unas 30 veces por segundo, para leer el mensaje que dibuja el addon. Las imágenes se quedan en memoria y nunca se guardan en disco. | `companion/askforever/capture/grabber.py` |
| Responde con IA | Envía tu pregunta, la conversación hasta ese momento y el contexto de tu personaje al proveedor de IA que hayas configurado (ver la tabla de abajo). | `companion/askforever/engine/`, `companion/askforever/providers/openai_compat.py` |
| Consulta la wiki | Cuando sus datos del juego no tienen la respuesta (nunca para rutas de viaje), busca en warcraft.wiki.gg con términos cortos. Se puede desactivar con `--no-web`. | `companion/askforever/web/wiki.py` |
| Muestra la respuesta | Abre una ventanita siempre encima del juego que ignora los clics (nunca coge el foco ni el teclado). | `companion/askforever/overlay/` |

### Qué se envía al proveedor de IA

Solo lo necesario para responder: tu **pregunta**, las preguntas y respuestas anteriores de la
misma conversación y el **contexto del personaje** que recoge el addon: nivel, raza, clase,
facción, zona y subzona, coordenadas del mapa, los títulos y niveles de las misiones de tu
registro y los identificadores de los puntos de vuelo que conoces. **Nunca** tu cuenta, el
nombre del personaje, el reino, el chat, tus amigos ni nada de fuera del juego.

El proveedor de IA recibe estos datos según sus propias condiciones de privacidad. Los planes
gratuitos pueden usar los datos para mejorar sus modelos: revisa las condiciones de tu
proveedor (enlaces en la guía de la clave de la API).

### Conexiones de red (lista completa)

| Destino | Cuándo | Para qué |
|---|---|---|
| El proveedor de IA que configuraste: Google Gemini (`generativelanguage.googleapis.com`), Groq (`api.groq.com`), Mistral (`api.mistral.ai`), Cerebras (`api.cerebras.ai`) u OpenRouter (`openrouter.ai`) | Cada vez que preguntas | Para obtener la respuesta |
| `warcraft.wiki.gg` | Solo cuando los datos del juego no tienen la respuesta (y nunca con `--no-web`) | Para consultar información |

Solo se contacta con el proveedor que elegiste. No hay más conexiones: ni comprobación de
actualizaciones, ni estadísticas, ni publicidad. La lista de proveedores está en
`companion/askforever/config.py`.

### Archivos y ajustes que toca

| Ubicación | Qué | Cuándo |
|---|---|---|
| Administrador de credenciales de Windows, entrada `AskForever` | Tu clave de la API | Al guardar la clave |
| `Interface\AddOns\AskForever` (en la carpeta del juego) | El propio addon y sus ajustes guardados (`WTF\...\SavedVariables\AskForever.lua`), que gestiona el juego | Al instalar el addon |
| `%LOCALAPPDATA%\AskForever\companion.log` | Registro de errores de la ventana de respuestas (rotativo, como mucho unos 4 MB). No contiene claves | Mientras el companion está abierto |
| `Interface\AddOns\AskForever_Slot*` | *Previsto (próximo milestone):* pequeños addons auxiliares que llevan la respuesta a la ventana del juego | — |

Previsto: el desinstalador borrará todo lo anterior (ver más abajo).

## Lo que el companion no hace nunca

- **No** lee ni escribe la memoria del juego, ni inyecta código ni ventanas en el proceso del
  juego.
- **No** simula teclado ni ratón, y no escribe en el chat.
- **No** captura nada fuera de esa franja de 512 × 32, ni guarda capturas de pantalla.
- **No** envía datos a nosotros ni a nadie aparte del proveedor de IA que elegiste y
  warcraft.wiki.gg.
- **No** se queda funcionando en segundo plano al cerrarlo ni arranca con Windows.

Son reglas de diseño del proyecto (ver las reglas de arquitectura del repositorio), no solo
promesas: el código es público para que cualquiera lo compruebe.

## Cómo comprobarlo tú mismo

Estado de cada comprobación (solo ponemos lo que existe de verdad hoy):

| Comprobación | Estado |
|---|---|
| Código fuente completo y público en GitHub | Disponible |
| Pruebas automáticas | Disponible (ejecuta `pytest` en `companion/`) |
| Programa compilado automáticamente en GitHub desde el código público (nunca en un ordenador personal) | Previsto para la primera versión pública |
| Hash SHA-256 de cada descarga publicado con la versión | Previsto |
| Atestación de procedencia de la compilación (`gh attestation verify <archivo> --repo warcrafted-server/AskForever`) | Previsto |
| Análisis de VirusTotal enlazado en cada versión | Previsto |
| Análisis automático del código (CodeQL) y actualización de dependencias (Dependabot) | Previsto |

## Por qué Windows puede mostrar un aviso

El programa no se distribuye por la Microsoft Store ni está firmado con un certificado de
pago, así que Windows SmartScreen puede decir que «ha protegido tu PC» de una aplicación no
reconocida. Ese aviso significa «Windows todavía no conoce este programa», no «este programa
es peligroso». Puedes comprobarlo con los pasos de arriba y después elegir **Más información →
Ejecutar de todas formas**. Si prefieres no hacerlo, puedes compilarlo tú mismo desde el
código fuente.

## Desinstalar sin dejar restos

*Previsto:* el instalador añade AskForever a «Aplicaciones instaladas» de Windows; al
desinstalarlo se borran el programa, sus accesos directos, el addon y sus addons auxiliares,
la clave de la API guardada y sus ajustes y registros.

## Avisar de un problema de seguridad

Consulta [SECURITY.md](../SECURITY.md).
