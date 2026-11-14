# AskForever game data / Datos del juego

This branch only holds the game database used by the AskForever companion. Pushing a new
`wow.sqlite.zip` with its `.sha256` and `DATA_VERSION` publishes a `data-YYYY.MM.DD` release
automatically (`.github/workflows/publish-data.yml`); the companion downloads it and checks
its SHA-256. The program's source code is in the `main` and `dev` branches.

Esta rama solo contiene la base de datos del juego que usa el companion de AskForever. Al subir
un `wow.sqlite.zip` nuevo con su `.sha256` y `DATA_VERSION` se publica sola una release
`data-AAAA.MM.DD`; el companion la descarga y comprueba su SHA-256. El código del programa está
en las ramas `main` y `dev`.
