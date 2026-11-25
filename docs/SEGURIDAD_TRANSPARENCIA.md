# Seguridad y transparencia

*English version: [SECURITY_TRANSPARENCY.md](SECURITY_TRANSPARENCY.md)*

AskForever tiene dos partes: el **addon** (funciona dentro del juego, como cualquier otro
addon) y **AskForever App** (una app para Windows y Linux que conecta el addon con la IA).
Esta página explica qué hace AskForever App y qué no hace nunca, para que decidas con todos
los datos. Todo lo que pone aquí se puede comprobar en el código fuente de este repositorio.

## En un minuto

- **Mira una pequeña franja de la ventana del juego** (512 × 32 píxeles en la esquina
  superior izquierda), donde el addon dibuja tu pregunta con píxeles de colores. Nada más de
  tu pantalla. En Linux, el portal de pantalla del escritorio comparte el monitor que elijas
  y un proceso local recorta esa franja (ver «En Linux»).
- Envía tu pregunta y algo de contexto del personaje al **proveedor de IA que tú elijas**, y
  puede consultar **warcraft.wiki.gg**. También contacta con GitHub para buscar actualizaciones de la app y los datos del juego.
- **Nunca** lee la memoria del juego, no inyecta nada en el juego y no pulsa teclas ni mueve
  el ratón por ti.
- Tu clave de API se guarda cifrada en el **Administrador de credenciales de Windows**, nunca
  en un archivo de texto (en Linux, en el llavero del escritorio).
- Sin cuentas, sin telemetría y sin servidores propios: no existe ningún servidor de
  AskForever.

## Qué hace AskForever App

| Qué | Detalle | Dónde está en el código |
|---|---|---|
| Encuentra la ventana del juego | Recorre las ventanas visibles y comprueba cuál es de `Wow.exe` (solo pide a Windows el nombre del proceso, con el permiso mínimo `PROCESS_QUERY_LIMITED_INFORMATION`; en Linux lee la lista de procesos de `/proc` y, del proceso `Wow.exe`, solo su línea de órdenes, su entorno y sus archivos mapeados, para saber su carpeta). | `companion/askforever/capture/window.py` |
| Lee la tira de píxeles | Captura solo una zona de 512 × 32 píxeles de la esquina superior izquierda de la ventana del juego, unas 30 veces por segundo, para leer el mensaje que dibuja el addon. Las imágenes se quedan en memoria y nunca se guardan en disco. | `companion/askforever/capture/grabber.py` |
| Responde con IA | Envía tu pregunta, la conversación hasta ese momento y el contexto de tu personaje al proveedor de IA que hayas configurado (ver la tabla de abajo). | `companion/askforever/engine/`, `companion/askforever/providers/openai_compat.py` |
| Consulta la wiki | Cuando sus datos del juego no tienen la respuesta (nunca para rutas de viaje), busca en warcraft.wiki.gg con términos cortos. | `companion/askforever/web/wiki.py` |
| Muestra la respuesta | Abre una ventanita siempre encima del juego que ignora los clics (nunca coge el foco ni el teclado). | `companion/askforever/overlay/` |
| Lee los datos del addon | Lee la carpeta `Interface\AddOns\AskForever\data` del addon para aplicar el parche de datos del juego y las fichas. No modifica esa carpeta. | `companion/askforever/data/patch.py` |
| Actualiza la app | Comprueba las versiones de GitHub al iniciar y cada seis horas. Descarga y verifica el instalador, espera a que termine cualquier respuesta en curso, ejecuta el instalador en silencio y vuelve a abrir la app. En Linux solo avisa de la versión nueva con su enlace. | `companion/askforever/app/selfupdate.py` |
| Actualiza los datos del juego | Busca en GitHub la base de datos que pide el addon instalado, la descarga y verifica, y después reconstruye la base local con el parche de datos del addon. | `companion/askforever/data/patch.py`, `companion/askforever/updates.py` |

### Qué se envía al proveedor de IA

Solo lo necesario para responder: tu **pregunta**, las preguntas y respuestas anteriores de la
misma conversación y el **contexto del personaje** que recoge el addon: nivel, raza, clase,
facción, zona y subzona, coordenadas del mapa, los títulos y niveles de las misiones de tu
registro, los identificadores de los puntos de vuelo que conoces y un resumen de tu personaje:
talentos aprendidos y puntos sin gastar, profesiones y habilidad, los nombres del equipo que llevas
puesto y tus estadísticas (salud, armadura, poder de ataque, crítico y similares). **Nunca** tu cuenta, el
nombre del personaje, el reino, el chat, tus amigos ni nada de fuera del juego.

El proveedor de IA recibe estos datos según sus propias condiciones de privacidad. Los planes
gratuitos pueden usar los datos para mejorar sus modelos: revisa las condiciones de tu
proveedor (enlaces en la guía de claves de API).

### Conexiones de red (lista completa)

| Destino | Cuándo | Para qué |
|---|---|---|
| El proveedor de IA que configuraste: Google Gemini (`generativelanguage.googleapis.com`), Groq (`api.groq.com`), Mistral (`api.mistral.ai`), Cerebras (`api.cerebras.ai`) u OpenRouter (`openrouter.ai`) | Cada vez que preguntas | Para obtener la respuesta |
| `warcraft.wiki.gg` | Solo cuando los datos del juego no tienen la respuesta | Para consultar información |
| API de GitHub (`api.github.com`) | Al iniciar la app y cada seis horas | Para comprobar si hay versiones nuevas de AskForever App; cuando hacen falta datos, para localizar la versión de la base de datos que pide el addon |
| Descargas de GitHub (`github.com` y `objects.githubusercontent.com`) | Al descargar una actualización de la app o una base de datos necesaria | Para descargar el instalador de la app o la base de datos. Se comprueba el SHA-256 de ambas descargas antes de usarlas. |

No hay más conexiones: ni estadísticas, ni publicidad ni servidores de AskForever. La lista de
proveedores está en `companion/askforever/config.py`; las actualizaciones de la app, en
`companion/askforever/app/selfupdate.py`; y las descargas de datos del juego, en
`companion/askforever/data/patch.py` y `companion/askforever/updates.py`.

### Archivos y ajustes que toca

| Ubicación | Qué | Cuándo |
|---|---|---|
| Administrador de credenciales de Windows, entrada `AskForever` | Tu clave de API cifrada | Al guardar la clave |
| `Interface\AddOns\AskForever\data` (en la carpeta del juego) | Parche de datos y fichas incluidos con el addon; solo lectura | Al aplicar los datos del addon instalado |
| `Interface\AddOns\AskForever` y `WTF\...\SavedVariables\AskForever.lua` | El addon y sus ajustes guardados, que gestiona el juego | Al instalar y usar el addon |
| `%LOCALAPPDATA%\Programs\AskForever` | Archivos de AskForever App | Al instalarla o actualizarla |
| `%LOCALAPPDATA%\AskForever\data` | Base de datos descargada y base reconstruida, además del estado del parche y las fichas | Cuando se necesitan datos del juego por primera vez o se actualizan |
| `%LOCALAPPDATA%\AskForever\logs\app.log` | Registro técnico de la app; no contiene claves de API | Mientras AskForever App está en marcha |
| `%LOCALAPPDATA%\AskForever\updates` | Instalador de actualización descargado y su archivo SHA-256, antes de instalar | Cuando hay una actualización de la app |

AskForever App lee la carpeta `data` del addon, pero no escribe en ella. En Windows, al
desinstalar la app no se elimina el addon; quítalo desde CurseForge o borra su carpeta, como
cualquier otro addon (en Linux, `uninstall.sh` sí lo borra; ver «En Linux»).

## Lo que AskForever App no hace nunca

- **No** lee ni escribe la memoria del juego, ni inyecta código o ventanas en el proceso del
  juego.
- **No** simula teclado ni ratón, y no escribe en el chat.
- **No** captura nada fuera de esa franja de 512 × 32, ni guarda capturas de pantalla. En
  Linux, el permiso del portal abarca el monitor entero, pero la app solo recibe el recorte
  local de 512 × 32 y no captura con el juego cerrado.
- **No** envía datos a nosotros ni a nadie aparte del proveedor de IA que elegiste,
  warcraft.wiki.gg y GitHub para actualizaciones y datos del juego.
- Al cerrar la ventana de la app, esta se oculta en la bandeja del sistema para que el addon
  pueda seguir funcionando. Si eliges **Salir** en la bandeja, la app se cierra.

Son reglas de diseño del proyecto (ver las reglas de arquitectura del repositorio), no solo
promesas: el código es público para que cualquiera lo compruebe.

## En Linux

AskForever App para Linux hace lo mismo que la de Windows, con estas diferencias (requisitos y
pasos completos en la [guía de instalación de Linux](https://github.com/warcrafted-server/AskForever/blob/main/docs/INSTALACION_LINUX.md)):

- **Captura:** el escritorio pide compartir pantalla y hay que elegir el monitor del juego; el
  permiso concedido al portal abarca ese monitor completo, pero un proceso local
  `gst-launch-1.0` recorta la esquina superior izquierda de 512 × 32 píxeles y la app solo
  recibe ese recorte. La elección se recuerda en `data/portal-token`; para elegir otro monitor,
  borrar ese archivo y reabrir la app. Solo captura mientras el juego está abierto.
- **Detección del juego:** lee la lista de procesos de `/proc` (la línea de órdenes, el entorno
  y los archivos mapeados del proceso `Wow.exe`, solo para saber su carpeta). No lee su
  memoria, no inyecta nada ni simula teclado o ratón.
- **Overlay:** usa X11 (XWayland) para consultar ventanas y dejar pasar los clics.
- **Clave:** en el llavero del escritorio (servicio `AskForever`), nunca en un archivo.
- **Archivos:** `<_forever_>/AskForever/` (programa, `data/`, `logs/`, `companion.log`,
  `data/portal-token`, `data/portal-geometry.json`); la carpeta `data/` del addon, en solo
  lectura; y, opcionalmente, `~/.local/share/applications/askforever.desktop`.
- **Conexiones de red:** las mismas que en Windows; de GitHub solo lee la lista de releases y
  descarga la base de datos del juego.
- **Actualizar y desinstalar:** la app solo avisa de una versión nueva con su enlace (no
  descarga ni ejecuta nada); para actualizar se cierra la app, se extrae el paquete nuevo y se
  ejecuta otra vez `./install.sh` (conserva la clave y los datos), y para desinstalar,
  `<_forever_>/AskForever/uninstall.sh`, que borra la clave, los datos, los registros, el
  addon, la carpeta de la app y el acceso directo.
- **Limitaciones conocidas:** con Wine/Proton en Wayland nativo el panel no se oculta al
  cambiar a otra ventana, y en GNOME el icono de bandeja necesita una extensión AppIndicator
  (no probado).

## Cómo comprobarlo tú mismo

Estado de cada comprobación (solo ponemos lo que existe de verdad hoy):

| Comprobación | Estado |
|---|---|
| Código fuente completo y público en GitHub | Disponible |
| Pruebas automáticas | Disponible: se ejecutan en GitHub en cada cambio (etiqueta CI) y en local con `pytest` en `companion/` |
| Programa compilado automáticamente en GitHub desde el código público (nunca en un ordenador personal) | Disponible desde la versión 0.3.0-beta.1 para Windows y desde la 0.5.0-beta.1 para Linux (ver el workflow Release en Actions) |
| Hash SHA-256 de cada descarga publicado con la versión | Disponible desde la versión 0.3.0-beta.1 (en Linux, desde la 0.5.0-beta.1; archivos `.sha256` y notas de la versión) |
| Atestación de procedencia de la compilación (`gh attestation verify <archivo> --repo warcrafted-server/AskForever`) | Disponible desde la versión 0.3.0-beta.1 (en Linux, desde la 0.5.0-beta.1), también para los datos del juego |
| Análisis de VirusTotal enlazado en cada versión | Disponible desde la versión 0.3.0-beta.3: [informe del instalador](https://www.virustotal.com/gui/file/882e541ae884519ebb20d147770122a857fb81c2f1f9ae8e477c12eb5ecfa077). Un motor lo marca (ver abajo). No hay informe de VirusTotal del paquete de Linux |
| Análisis automático del código (CodeQL) y actualización de dependencias (Dependabot) | Disponible (ver las etiquetas del README) |

## Detecciones de antivirus

Publicamos el informe de VirusTotal de cada instalador de Windows, también las detecciones que creemos que son falsos positivos. Del paquete de Linux no hay análisis publicado.

- **0.3.0-beta.3:** un motor, **SecureAge**, marca el instalador con la etiqueta genérica «Malicious» (sin nombrar ninguna familia de malware); el resto de motores no detecta nada. El archivo es el compilado en GitHub (su SHA-256 coincide con el `.sha256` publicado en la versión). Los motores heurísticos suelen marcar así los instaladores sin firmar hechos con PyInstaller e Inno Setup. Lo comunicamos al fabricante como falso positivo y actualizaremos esta página con su respuesta.

Si un antivirus marca AskForever, puedes comprobar el hash y la procedencia de la compilación con los pasos de arriba, leer el código fuente o compilarlo tú mismo.

## Por qué Windows puede mostrar un aviso

El programa no se distribuye por la Microsoft Store ni está firmado con un certificado de
pago, así que Windows SmartScreen puede decir que «ha protegido tu PC» de una aplicación no
reconocida. Ese aviso significa «Windows todavía no conoce este programa», no «este programa
es peligroso». Puedes comprobarlo con los pasos de arriba y después elegir **Más información →
Ejecutar de todas formas**. Si prefieres no hacerlo, puedes compilarlo tú mismo desde el
código fuente.

## Desinstalar sin dejar restos

AskForever App aparece en **Configuración > Aplicaciones** de Windows. Al desinstalarla se
eliminan la app, sus accesos directos, la clave de API guardada y los datos, registros y
archivos de actualización locales de AskForever. Quita el addon `AskForever` por separado
desde la app de CurseForge o borrando su carpeta, como cualquier otro addon.

En Linux, ejecuta `<_forever_>/AskForever/uninstall.sh` (`--yes` para no preguntar) con la app
cerrada: borra la clave, los datos, los registros, el addon, la carpeta de la app y el acceso
directo.

## Avisar de un problema de seguridad

Consulta [SECURITY.md](../SECURITY.md).
