# TODO

El detalle de cada milestone está en [ROADMAP.md](ROADMAP.md).

## Alta
- Publicar la v0.1.0-beta.1 cuando Marc lo decida, siguiendo [docs/CURSEFORGE.md](docs/CURSEFORGE.md): subir el zip (`scripts/build-release.ps1`) a CurseForge desde su cuenta y, después, push, tag y release en GitHub.
- Milestone 2 · v0.2.0-beta: transporte por tira de píxeles + respuesta en overlay (punto de decisión: ¿funciona la captura en Forever?).

## Media
- Milestones 3–7 del roadmap (slots LoD, instalador, rutas, robustez, multi-proveedor).
- Icono propio (`.tga`) para el retrato y el minimapa: hoy se usa el libro del juego (constante en `ui/Theme.lua` y `ui/Minimap.lua`).
- Instalar `luacheck` si el volumen de errores lo justifica (el ejecutable externo se denegó).
- Validar en el juego el atajo de teclado (Opciones → Atajos → AddOns) tal como lo describen las guías.

## Baja
- Contenido (misiones, NPCs, RAG de guías) y lanzamiento estable v1.0.0.

## Descartado
- Simular input, leer memoria del proceso o inyectar overlays: vulnera las reglas del juego y arriesga baneos.
