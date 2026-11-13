# Guía de instalación de AskForever (ES)

**[English version](INSTALL_GUIDE.md)**

> 🚧 Borrador para la **v0.1.0-beta**, que todavía no está publicada. Los pasos se comprobarán en el juego antes de publicar y esta guía se actualiza con cada versión. Si algún paso no coincide con lo que ves, revisa la última versión en GitHub.

Tiempo estimado: **2 minutos**, una sola vez.

## Qué hace la v0.1.0

La v0.1.0 solo contiene el **addon**. Recoge el contexto de tu personaje (nivel, raza, clase, facción, zona, coordenadas, misiones activas) y construye un prompt listo para copiar y pegar en cualquier chat de IA (Gemini, ChatGPT, Claude…). Recibir la respuesta dentro del juego requiere el **companion**, que llegará en versiones posteriores (consulta la [hoja de ruta](../ROADMAP.md)).

## Requisitos

- WoW Forever instalado.
- Nada más para la v0.1.0.

## 1. Instalar el addon

### Opción A: aplicación de CurseForge (recomendada)
1. Abre la app de **CurseForge** → **World of Warcraft**.
2. Comprueba que está seleccionada la instalación **Forever**. Si no aparece, usa *Scan for games* o añade a mano la carpeta `World of Warcraft\_forever_`.
3. Busca **AskForever** y pulsa **Install**.

### Opción B: manual
1. Descarga el `.zip` desde la página de AskForever en CurseForge (pestaña **Files**).
2. Descomprímelo y copia la carpeta `AskForever` en `World of Warcraft\_forever_\Interface\AddOns\`.
3. Debe quedar así: `...\AddOns\AskForever\AskForever.toc`

## 2. Iniciar el juego

Si el juego estaba abierto, **ciérralo del todo y vuelve a abrirlo**: `/reload` no detecta addons nuevos. En la selección de personaje, pulsa **AddOns** y comprueba que **AskForever** está activado.

## 3. Haz tu primera pregunta

1. Entra con tu personaje.
2. Abre AskForever con `/af` (o `/askforever`), o con el atajo que configures en *Opciones → Atajos → AddOns → AskForever*.
3. Escribe tu pregunta, por ejemplo: *¿por dónde voy a Baldíos?*
4. Pulsa **Copiar prompt**. Aparece una caja con el prompt ya seleccionado: pulsa `Ctrl+C`.
5. Pégalo en el chat de IA que prefieras. No hace falta decir tu nivel, facción ni dónde estás: el prompt ya los incluye.

El botón del minimapa abre y cierra la ventana. Arrástralo para moverlo; `/af minimap` lo muestra u oculta.

## Solución de problemas

| Problema | Solución |
|---|---|
| `/af` no hace nada | AskForever no está activado o no reiniciaste el juego tras instalarlo. Revisa el paso 2. |
| Sale un error al entrar | Instala **BugSack** y **BugGrabber**, repite el error y abre una [incidencia en GitHub](https://github.com/warcrafted-server/AskForever/issues) con el texto. |
| El prompt muestra una zona equivocada o no hay misiones | Vuelve a abrir la ventana tras cambiar de zona; si persiste, avísanos. |
| La ventana se ha perdido fuera de la pantalla | Ejecuta `/af reset` para restaurar su posición (disponible desde la v0.1.0). |

## Desinstalar

Desinstálalo desde la app de CurseForge o borra `Interface\AddOns\AskForever`. Tus ajustes están en `WTF\Account\<cuenta>\SavedVariables\AskForever.lua` (borrarlos es opcional).

## Preguntas frecuentes

**¿Es gratis?** Sí.

**¿Me pueden banear?** AskForever no simula teclas, no lee la memoria del juego ni automatiza acciones: solo muestra información con la API oficial de addons. Aun así, Blizzard no se ha pronunciado sobre este tipo de herramientas, así que no se puede garantizar nada. Úsalo bajo tu responsabilidad.

**¿Qué datos maneja?** Tu pregunta y el contexto de tu personaje. En la v0.1.0 no se envía nada a ningún sitio: tú decides qué pegas y dónde.

**¿Funciona en Mac o Linux?** El addon funciona donde funcione el juego. El companion (versiones futuras) será solo para Windows al principio.
