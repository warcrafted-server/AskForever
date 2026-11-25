# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/). Versioning: [SemVer](https://semver.org/). English first, then Spanish / Inglés primero, después español.

## [Unreleased]

### English
- Corrected (internal, Linux version in preparation): the Linux dependency of the screen capture is declared, the packaged program no longer forces the Windows credential store outside Windows and the set-key hint names the right command.
- Added (internal, Linux version in preparation): the companion asks XWayland for the game window's real position and size, and whether it is active, instead of always assuming a provisional 1920×1080 frame at the top-left corner.
- Added (internal, Linux version in preparation): the overlay is shown over the game on Linux (XWayland), always on top, click-through and without taking focus, and hides when the game is not the active window.
- Added (internal, Linux version in preparation): the companion shows its icon in the Linux notification area (StatusNotifierItem), with Open and Quit in the context menu, and uses desktop notifications instead of balloons.
- Added (internal, Linux version in preparation): on Linux the updater only announces a new release with its link; it never downloads or runs anything.
- Added (internal, Linux version in preparation): on Linux the companion translates the game path Wine reports into a real Unix path, so addon data and uninstall find the game folder, and the new `find-wow` command lists the WoW Forever folders it detects.
- Added (internal, Linux version in preparation): the packaged Linux app finds the game folder from its own location, so addon data and uninstall work with the game closed, and uninstalling a copy never touches another installation's addon.

### Español
- Corregido (interno, versión para Linux en preparación): se declara la dependencia de la captura de pantalla en Linux, el programa empaquetado ya no fuerza el almacén de claves de Windows fuera de Windows y el aviso de set-key nombra la orden correcta.
- Añadido (interno, versión para Linux en preparación): el companion pregunta a XWayland la posición y el tamaño reales de la ventana del juego, y si está activa, en lugar de suponer siempre un marco provisional de 1920×1080 en la esquina superior izquierda.
- Añadido (interno, versión para Linux en preparación): el overlay se muestra sobre el juego en Linux (XWayland), siempre encima, transparente a los clics y sin robar el foco, y se oculta cuando el juego no es la ventana activa.
- Añadido (interno, versión para Linux en preparación): el companion muestra su icono en el área de notificación de Linux (StatusNotifierItem), con Abrir y Salir en el menú contextual, y usa notificaciones del escritorio en lugar de globos.
- Añadido (interno, versión para Linux en preparación): en Linux el actualizador solo avisa de una versión nueva con su enlace; nunca descarga ni ejecuta nada.
- Añadido (interno, versión para Linux en preparación): en Linux el companion traduce a una ruta real de Unix la ruta del juego que informa Wine, de modo que los datos del addon y la desinstalación encuentran la carpeta del juego, y la nueva orden `find-wow` lista las carpetas de WoW Forever que detecta.
- Añadido (interno, versión para Linux en preparación): la aplicación empaquetada de Linux localiza la carpeta del juego a partir de su propia ubicación, de modo que los datos del addon y la desinstalación funcionan con el juego cerrado, y desinstalar una copia nunca toca el addon de otra instalación.

## [0.4.0-beta.12] - 2026-11-24

### English
- Updated (November 23 and 24 guides): Retribution Paladin follows the rewritten Wowhead guides (stat priority from simulators with hit, expertise, crit and haste; strengths and PvP limits; the Shockadin PvP build now takes Oath of Light); Subtlety Rogue builds take Improved Ambush; the Discipline Priest PvP build takes Holy Binding and full Inspiration; Legacy respec costs 10 gold the first time and 20 the second; companions can also come from the Black Market Auction House in Riverglades.
- Updated: game data from the new wowdata update (for example, the Spanish name of the Totem of the Storm).
- Added: the assistant tells you where to spend your next talent point, which talents to have at a given level and which abilities you learn at a level, computed from the Wowhead talent orders (it never mixes builds: if several fit, it lists them so you pick one).
- Added: where to plant herb seeds (Greenhouse and Seed Hybridizer at your campsite).
- Corrected: herb and ore names now come in Spanish (for example Hojaplata, Flor de paz).
- Updated: 300+ guide cards checked against the guides Wowhead rewrote in a new format (Fishing, Cooking, Legacy, PvP, dungeon quests); the beta-only PvP cost and ranking cards and the closed-beta sentence are gone.
- Data patch 2026.11.24.6.
- Changed (internal): development tools find wowdata at its new location and bring the guides and change reports that wowdata copies from the Wowhead download, without ever deleting retired guides.

### Español
- Actualizado (guías del 23 y 24 de noviembre): el Paladín Reprensión sigue las guías reescritas de Wowhead (prioridad de estadísticas de simuladores con golpe, pericia, crítico y celeridad; puntos fuertes y límites en JcJ; la build JcJ de Choque Sagrado lleva Juramento de luz); las builds de Pícaro Sutileza llevan Emboscada mejorada; la build JcJ del Sacerdote Disciplina lleva Vinculación sagrada e Inspiración completa; reasignar Legacy cuesta 10 de oro la primera vez y 20 la segunda; las mascotas también pueden salir de la casa de subastas del mercado negro de Clarofluvial.
- Actualizado: datos del juego de la nueva actualización de wowdata (por ejemplo, el nombre del Tótem de la Vorágine).
- Añadido: el asistente dice dónde gastar tu siguiente punto de talento, qué talentos tener a un nivel y qué habilidades aprendes a un nivel, calculado con el orden de talentos de Wowhead (nunca mezcla builds: si encajan varias, las lista para que elijas).
- Añadido: dónde plantar semillas de hierba (Invernadero e Hibridador de semillas en tu campamento).
- Corregido: los nombres de hierbas y minerales llegan en español (por ejemplo Hojaplata, Flor de paz).
- Actualizado: más de 300 fichas de la guía comprobadas con las guías que Wowhead reescribió en un formato nuevo (Pesca, Cocina, Legacy, JcJ, misiones de mazmorra); se quitan las fichas de costes y clasificaciones de JcJ de la beta y la frase de la beta cerrada.
- Parche de datos 2026.11.24.6.
- Cambiado (interno): las herramientas de desarrollo encuentran wowdata en su nueva ubicación y traen las guías y los informes de cambios que wowdata copia de la descarga de Wowhead, sin borrar nunca las guías retiradas.

## [0.4.0-beta.11] - 2026-11-24

### English
- Updated: the guide cards now follow the November 19 guide update: Hunter (Auto Shot, Beast Mastery, Survival weaving rotation and talent builds), class stats, builds and enchants, PvP (weekly Field of Honor quests, battlemaster locations, rank points, gear costs, Darkspear Islands) and the raids (entrances, boss counts, no attunement for the two new ones).
- Added: Maraudon quest list, Timbermaw Hold reputation from Azshara and Blackmaw Hold, and new drop details for the Tarnished Undermine Real.
- Corrected: weapon skills can be trained from level 10 (Polearms from level 20).
- Updated (November 21 guides): Hunter stat priorities now include haste and no longer call them speculative; Hunter enchants and combat consumables follow the current lists; Ta'shkal joins the fastest-attacking pets; Marksmanship mana weakness; Restoration Shaman Ghost Wolf build; Dartol's Rod toy replica; Arathi Basin battlemaster location in Thunder Bluff.
- Corrected: when you ask where to spend a talent point, the assistant now receives the maximum rank of each talent you already have, so it no longer invents ranks (it said Focused Fire 3/3; it has 2).
- Updated (November 23 guides): Fury Warrior Rage now grants extra Rage on critical hits and the new Reckless Swings talent; Protection Warrior stats with Block Value; Elemental Shaman stats with haste first; Feral Druid tank offensive stats; Arcane Mage gloves enchant; Holy Priest leveling build; PvP rank vendors and Alterac Valley giving no Rank Points; Cozy Sleeping Bag bonus lasting 2 hours; Legacy respec cost; Razorfen Downs levels 37-46; fishing tournament with 250 winners; Tailoring trainer ranks.
- Updated (November 24 data): the Expert Fishing book is tradeable, so it can also be on the Auction House; fishing skill for 39 zones, positions of several NPCs and quest givers observed in game, and the current Questie data (it only fills gaps left by the client, observations and Wowhead).
- Changed (internal): the companion code is being prepared for a future Linux version (screen capture, paths, single instance). Nothing changes on Windows.
- Data patch 2026.11.24.2.

### Español
- Actualizado: las fichas de la guía siguen la actualización de guías del 19 de noviembre: Cazador (Disparo automático, Bestias, rotación de Supervivencia con cambio de arma y builds de talentos), estadísticas, builds y encantamientos de las clases, JcJ (misiones semanales del Campo de Honor, ubicación de maestros de batalla, puntos de rango, costes del equipo, Islas Lanza Negra) y las bandas (accesos, número de jefes, sin sintonización en las dos nuevas).
- Añadido: lista de misiones de Maraudon, reputación de los Fauces de Madera desde Azshara y el Bastión Faucenegra, y nuevos datos de caída del Real deslustrado de Minahonda.
- Corregido: las habilidades de armas se aprenden desde el nivel 10 (Armas de asta, desde el 20).
- Actualizado (guías del 21 de noviembre): las prioridades de estadísticas del Cazador incluyen la celeridad y ya no se llaman especulativas; encantamientos y consumibles de combate del Cazador según las listas actuales; Ta'shkal entra entre las mascotas de ataque más rápido; debilidad de maná de Puntería; build de Lobo fantasmal del Chamán Restauración; réplica de la Vara de Dartol como juguete; ubicación del maestro de batalla de la Cuenca de Arathi en Cima del Trueno.
- Corregido: al preguntar dónde gastar un punto de talento, el asistente recibe el rango máximo de cada talento que ya tienes y no inventa rangos (decía Fuego enfocado 3/3; tiene 2).
- Actualizado (guías del 23 de noviembre): la furia de Furia da furia extra con los críticos y el talento nuevo Golpes temerarios; estadísticas del Guerrero Protección con valor de bloqueo; estadísticas del Chamán Elemental con la celeridad primero; estadísticas ofensivas del Druida feral tanque; encantamiento de guantes del Mago Arcano; build de subida del Sacerdote Sagrado; vendedores de rango JcJ y Valle de Alterac sin Puntos de Rango; bonus del Saco de dormir acogedor de 2 horas; coste de reasignar Legacy; niveles de Zahúrda Rajacieno 37-46; torneo de pesca con 250 ganadores; rangos de instructores de Sastrería.
- Actualizado (datos del 24 de noviembre): el libro de Pesca para expertos se puede comerciar, así que también puede estar en la casa de subastas; habilidad de pesca de 39 zonas, posiciones de varios PNJ y dadores de misión observados en el juego, y los datos actuales de Questie (solo rellenan lo que no dan el cliente, lo observado ni Wowhead).
- Cambiado (interno): el código del companion se prepara para una futura versión para Linux (captura de pantalla, rutas, instancia única). En Windows no cambia nada.
- Parche de datos 2026.11.24.2.

## [0.4.0-beta.10] - 2026-11-21

### English
- Corrected: opening another window (talents, bags…) closes the AskForever window; reopening it right away now keeps the conversation instead of losing the answers (a new conversation starts only after 2 minutes closed).

### Español
- Corregido: al abrir otra ventana (talentos, mochilas…) se cierra la de AskForever; si la reabres enseguida, la conversación continúa y ya no se pierden las respuestas (la conversación nueva empieza tras 2 minutos cerrada).

## [0.4.0-beta.9] - 2026-11-20

### English
- Added: the assistant now knows class talents can be forgotten (reset button in the talent window, it costs gold) and no longer mixes it up with respeccing Legacy Points.
- Added: the addon now sends a summary of your character (learned talents and unspent points, professions, worn gear and stats) so the assistant can answer questions about you, such as reviewing your talents. Nothing is sent that identifies you: no name, realm or gold.
- Changed: if the summary is missing, it says how many talent points the player should have at their level and that it cannot see what was spent.
- Data patch 2026.11.20.1.

### Español
- Añadido: el asistente sabe ahora que los talentos de clase se pueden olvidar (botón de restablecer en la ventana de talentos, cuesta oro) y ya no lo confunde con reasignar puntos Legacy.
- Añadido: el addon envía ahora un resumen de tu personaje (talentos aprendidos y puntos sin gastar, profesiones, equipo puesto y estadísticas) para que el asistente responda preguntas sobre ti, como revisar tus talentos. No se envía nada que te identifique: ni nombre, ni reino, ni oro.
- Cambiado: si falta el resumen, dice cuántos puntos de talento corresponden al nivel y que no ve lo que se ha gastado.
- Parche de datos 2026.11.20.1.

## [0.4.0-beta.8] - 2026-11-19

### English
- Fixed: the assistant now finds the new enchant and consumable guides with everyday questions such as "what consumables do I use as a warlock" or "what do I enchant as a mage" (it missed some of them before).
- Data patch 2026.11.19.4.

### Español
- Corregido: el asistente encuentra ahora las guías nuevas de encantamientos y consumibles con preguntas cotidianas como «qué consumibles uso de brujo» o «qué encanto siendo mago» (antes se le escapaban algunas).
- Parche de datos 2026.11.19.4.

## [0.4.0-beta.7] - 2026-11-19

### English
- Added: enchant and consumable guides for Druid (Balance, Feral, Restoration), Hunter, Mage (including mage scrolls), Paladin, Rogue, Shaman, Warlock and Warrior: what to enchant per slot and level, level 60 upgrades, elixirs, potions, weapon buffs, food and what stacks. Priest is left out because its Wowhead pages are written for the level 30 beta.
- Data patch 2026.11.19.3.

### Español
- Añadido: guías de encantamientos y consumibles del Druida (Equilibrio, Feral, Restauración), Cazador, Mago (con los pergaminos de mago), Paladín, Pícaro, Chamán, Brujo y Guerrero: qué encantar por hueco y nivel, mejoras de nivel 60, elixires, pociones, mejoras de arma, comida y qué se acumula. El Sacerdote queda fuera porque sus páginas de Wowhead están hechas para la beta de nivel 30.
- Parche de datos 2026.11.19.3.

## [0.4.0-beta.6] - 2026-11-19

### English
- Added: best-in-slot gear answers. Asking for "BiS" or the best gear of a class and specialization lists the best item per slot with where it drops, from the guide data (only for specializations that have data; otherwise it says which ones do).

### Español
- Añadido: respuestas de equipo BiS. Al preguntar por el BiS o el mejor equipo de una clase y especialización se lista el mejor objeto de cada ranura con su origen, a partir de los datos de las guías (solo para las especializaciones con datos; si no, indica cuáles tienen).

## [0.4.0-beta.5] - 2026-11-19

### English
- Added: ability details for Druid (bear and cat kits, Tranquility and Barkskin, Revive and Rebirth), Hunter (Marksmanship shot timings, Survival melee attacks, stings and utilities) and Mage (Research and Comprehend Scroll, Amplify and Dampen Magic in groups, Arcane Power, Combustion and Pyroblast), Paladin (blessings, Judgement effects per seal, immunities and Forbearance, resistance auras and anti-undead tools), Rogue (combo move costs, stealth openers, utility durations, poisons) and Priest (racial abilities, damage spells, utility levels and durations), Shaman (group buff, cleansing and water totems, damage cooldowns), Warlock (demon abilities, Inferno, Ritual of Doom and Soulstone) and Warrior (cooldown, defense and debuff numbers).

### Español
- Añadido: detalle de habilidades del Druida (oso y felino, Tranquilidad y Pielcorteza, Revivir y Renacer), del Cazador (tiempos de los disparos de Puntería, ataques cuerpo a cuerpo de Supervivencia, picaduras y utilidades) y del Mago (Investigar y Entender pergamino, Amplificar y Empapar magia en grupo, Poder Arcano, Combustión y Piroexplosión), del Paladín (bendiciones, efectos de Sentencia por sello, inmunidades y Abstención, auras de resistencia y herramientas contra no-muertos), del Pícaro (costes de los ataques de combo, aperturas de sigilo, duración de utilidades y venenos) y del Sacerdote (habilidades raciales, hechizos de daño, niveles y duraciones de utilidades), del Chamán (tótems de mejora, de limpieza y de agua, enfriamientos de daño), del Brujo (habilidades de demonios, Inferno, Ritual de condena y Piedra de alma) y del Guerrero (cifras de enfriamientos, defensas y debilitaciones).

## [0.4.0-beta.4] - 2026-11-19

### English
- Added: Hunter pets (rare pets, trainer abilities and training points, extra abilities of each family) and Shaman Stormcaller build (31/20/0, rotation, how it differs from Elemental).
- Changed: every addon version is now uploaded to CurseForge as a release.

### Español
- Añadido: mascotas del Cazador (mascotas raras, habilidades del instructor y puntos de entrenamiento, habilidades extra de cada familia) y build Stormcaller del Chamán (31/20/0, rotación y en qué se diferencia de la Elemental).
- Cambiado: cada versión del addon se sube ahora a CurseForge como release.

## [0.4.0-beta.3] - 2026-11-18

### English
- Added: new special quests and secrets chapter (the level 50 class quest in the Sunken Temple for every class, Dawn Waker, Night Watchman's Torch, the Alcaz disguise and Rainbow Generator toys, library books, the Scarlet banner puzzle), the Darkmoon Faire (dates, tickets, reputation, decks, blessings) and collecting (mounts, pets, toys and cosmetics).
- Added: new interface chapter (edit mode, damage meter, Discord guild chat, pings and macros) and the PvP chapter rewritten from the latest guides (rank system, Honor and Rank Points, rewards per rank, seasons, the Darkspear Isles battleground).
- Added: professions guide from the latest WoW Forever guides: slots, ranks and trainers, Legacy perks and camp stations, recommended professions per class, Craftsman's Writs, weapon skills, how to level every gathering and secondary profession by range, and what each crafting profession makes with its specializations.
- Added: new trade and reputation chapter: the Azeroth Commerce Authority and Durotar Supply and Logistics, Merchant's Favor and profession titles, the Tarnished Undermine Real, and the Gelkis and Magram centaurs, Nightclaw druids, Shen'dralar and Timbermaw Hold reputations (how to raise them and their rewards).
- Added: dungeon and raid guide from the latest WoW Forever guides: for every dungeon, its level and how to reach the entrance from each faction, the quests worth picking up before going in, one card per boss with its key mechanics and the notable rewards; how dungeons and the nine new ones work, raid dates, sizes and locations, the full Onyxia attunement for each faction, season 1 tier set bonuses per class and the PvE tier lists for DPS, healers and tanks.
- Added: the races guide gets the new race and class combinations.

### Español
- Añadido: nuevo capítulo de misiones especiales y secretos (la misión de clase de nivel 50 del Templo de Atal'Hakkar para cada clase, Dawn Waker, la antorcha del vigilante nocturno, los juguetes del disfraz de Alcaz y el Generador de arcoíris, los libros de biblioteca, el rompecabezas del Estandarte Escarlata), la Feria de la Luna Negra (fechas, fichas, reputación, barajas y bendiciones) y el coleccionismo (monturas, mascotas, juguetes y apariencias).
- Añadido: nuevo capítulo de interfaz (modo de edición, medidor de daño, chat de hermandad en Discord, pings y macros) y el capítulo de JcJ rehecho con las últimas guías (sistema de rangos, Honor y Puntos de Rango, recompensas por rango, temporadas y el campo de batalla Islas Lanza Negra).
- Añadido: guía de profesiones a partir de las últimas guías de WoW Forever: plazas, rangos e instructores, ventajas Legacy y estaciones de campamento, profesiones recomendadas por clase, Escrituras del artesano, habilidades de armas, cómo subir cada profesión de recolección y secundaria por tramos y qué fabrica cada profesión de artesanía con sus especializaciones.
- Añadido: nuevo capítulo de comercio y reputaciones: la Autoridad Comercial de Azeroth y Suministros y Logística de Durotar, el Favor de mercader y los títulos de profesión, el Real deslustrado de Minahonda, y las reputaciones de los centauros Gelkis y Magram, los druidas Garranoche, los Shen'dralar y los Fauces de Madera (cómo subirlas y sus recompensas).
- Añadido: guía de mazmorras y bandas a partir de las últimas guías de WoW Forever: de cada mazmorra, su nivel y cómo llegar a la entrada desde cada facción, las misiones que conviene recoger antes, una ficha por jefe con sus mecánicas clave y las recompensas destacadas; cómo funcionan las mazmorras y las nueve nuevas, fechas, tamaños y ubicación de las bandas, la sintonización completa de Onyxia para cada facción, las bonificaciones de los conjuntos de la temporada 1 por clase y las clasificaciones JcE de DPS, sanadores y tanques.
- Añadido: la guía de razas incluye las nuevas combinaciones de raza y clase.

## [0.4.0-beta.2] - 2026-11-18

### English
- Added: guide cards from the latest WoW Forever guides for travel and mounts (flight points, ships, zeppelins and tram, riding costs, class mounts, mount and pet collections, Riverglades, Zephra's Isle), first steps (Legacy system, bags, bank and storage, camping, cozy sleeping bag, editions and roadmap) and the Skyborne race.
- Changed: class guide cards updated to the latest WoW Forever class guides. Rogue: level 60 builds (new Combat Venom and Subtlety Hemorrhage + Seal Fate builds, superseded builds removed), rotations and new opening sequences for each spec. Druid: Balance raid and PvP builds and the Feral leveling build and rotation. Warrior: Fury leveling rotation with Reckless Swings. Mage: Arcane Power sequence. The new data reaches the app through the addon, without reinstalling it.
- Changed: app releases on GitHub are now regular releases marked as latest (betas included), and data releases are published automatically as pre-releases.
- Fixed: the addon data patch no longer resends whole tables when only the "last seen" date of the data changes.

### Español
- Añadido: fichas de la guía a partir de las últimas guías de WoW Forever sobre viajes y monturas (puntos de vuelo, barcos, zepelines y tranvía, coste de equitación, monturas de clase, colecciones de monturas y mascotas, Clarofluvial, isla de Zephras), primeros pasos (sistema Legacy, bolsas, banco y almacenamiento, campamentos, saco de dormir, ediciones y calendario) y la raza Cielonato.
- Cambiado: fichas de clase actualizadas a las últimas guías de clase de WoW Forever. Pícaro: builds de nivel 60 (nuevas builds de Combate con Veneno y de Sutileza con Hemorragia y Sello del destino, se retiran las superadas), rotaciones y aperturas nuevas por especialización. Druida: builds de Equilibrio para banda y JcJ y build y rotación Feral para subir. Guerrero: rotación de Furia para subir con Golpes temerarios. Mago: secuencia de Poder Arcano. Los datos nuevos llegan a la app por el addon, sin reinstalarla.
- Cambiado: las releases de la app en GitHub pasan a ser releases normales marcadas como la última (también las betas), y las de datos se publican automáticamente como prerrelease.
- Corregido: el parche de datos del addon ya no reenvía tablas enteras cuando solo cambia la fecha de «última vez visto» de los datos.

## [0.4.0-beta.1] - 2026-11-18

### English
- Added: the VirusTotal report of the installer is linked from the README badge and the security and transparency page, which also explains the single detection (SecureAge, generic label) of 0.3.0-beta.3.
- Added: the development copy loads as AskForever (dev) next to the public addon, with a warning when both are enabled.
- Added: the addon sends the position of its conversation panel and tells the companion when its window opens, closes or moves (for the in-window chat).
- Added: chat inside the addon window: the companion draws the whole conversation over the addon's conversation panel and follows the window when it opens, closes or moves; without that information it keeps the classic answer window.
- Fixed: quest givers and turn-in NPCs are chosen for your faction (an Alliance player was sent to Undercity), same-name quests are picked for your faction, and locations in your current zone come first.
- Added: general gameplay questions receive the official game texts that match them (tutorials, beginner interface help and loading-screen tips), with their reference.
- Added: questions about where to find a banker, innkeeper, auctioneer, flight master, stable master or profession trainer list the NPCs of that city or zone with coordinates.
- Fixed: the zones suggested for your level no longer include the other faction's zones.
- Added: hunters asking about pets get the tameable beasts of their zone (family, level and coordinates) seen in game.
- Fixed: the official game texts are found more often and more precisely: tutorial titles count ("Death" for "I died"), race and class tutorials only reach that race and class, and words such as "items" or "quests" are no longer ignored.
- Fixed: a short follow-up question ("and for levelling, which one?") keeps the topic of the previous one instead of answering only about the new word.
- Fixed: a single word of the question no longer picks a minor place as the zone ("hunter" chose a ship called "The Dawnchaser"); only main zones are matched that way.
- Added: verified beginner guide sections, each with its sources, used for general questions: what WoW Forever is, maximum level, new zones, dungeons and raids, the new Skyborne race and class combinations, the Legacy system and its perks and rewards, the experience preset and realm types.
- Fixed: asking which dungeon you can do below the first dungeon level now lists the first ones you will be able to do, and dungeons inside the other faction's capital cities are no longer suggested.
- Changed: the AI only mentions the zones for your level when you ask where to go or what to do, and no longer adds districts or buildings that are not in the data when saying where something is.
- Added: beginner guide on professions (how many you can have, what each one does, good pairings, secondary professions).
- Added: stat priority for every class specialization and, verified from the game client, the level of your first talent point (10) and how many you get per level.
- Added: talent questions get exact WoW Forever data: what a talent does at each rank, its tree, the points it needs and its prerequisite, the talents of a tree, and which talents are new or changed in Forever.
- Added: beginner guide on races (classes each race can be in WoW Forever, racial abilities, the Skyborne).
- Added: beginner guide on first steps (presets, camping, sleeping bag, surnames, transmog, controller and more) and on travel and mounts.
- Added: beginner class guides (roles, what changed in Forever, leveling spec and talent path, class quests and mechanics): Hunter, Warrior, Mage, Paladin, Priest, Rogue, Shaman, Warlock, Druid
- Added: beginner dungeon guide (how to get to each dungeon, what to expect, key mechanics and the quests to pick up before going in).
- Added: beginner PvP guide (modes, honor and ranks, strong specs).
- Fixed: Hall of Thanes and Ruins of Lordaeron (new dungeons inside a capital) are suggested to both factions, and their level ranges in the guide match the WoW Forever table.
- Added: for general questions the AI first picks, from a table of contents of the guide, the sections that answer them (falls back to keyword search if it fails); can be turned off with ASKFOREVER_GUIDE_ROUTER=0.
- Fixed: "level up" questions were taken as travel questions ("ir de" inside "subir de nivel"); sections of another race or class are only used when the question names it; follow-ups starting with "but" or "then" keep the previous topic; the AI gives guide recommendations with their reason; the sleeping bag questline step by step and which hunter pet to pick for levelling.
- Fixed: the sections chosen by the AI go first even when keyword search had already found them (they could be cut), "when can I go by horse?" is no longer a travel question, and one-word quest names ("Attention!") only match when the question talks about quests.
- Changed: the AI states facts directly without saying where they come from ("according to the guide").
- Fixed: the guide router has room for long section ids and more time to answer (they were cut and it fell back to keyword search).
- Fixed: guide sections reach the AI with their title and complete (the data block for guide answers is twice as long), so builds are no longer cut or mixed up; the wiki is no longer searched when a guide section already answers, so talents from other game versions stop leaking in.
- Changed: the AI gives builds in full with every rank, knows how many talent points you have at your level (and stops there when you ask what you should have), answers questions about other classes, and does not fill builds with talents from other game versions.
- Fixed: build and talent path sections say what they are for (raids, dungeons, PvP or levelling), so the AI no longer says it has no raid build when it has one.
- Added: asking which quests there are in a zone (or here) for your level lists them with who gives them and where; asking for a boat without naming a port lists the known boats, zeppelins and trams; ambiguous questions get a question back instead of "I do not know".
- Fixed: long answers (complete builds, "tell me everything") are no longer cut at 900 characters; the AI no longer starts answers with the internal data label; "any other options?" keeps the topic of the previous question; asking which quests there are here when you have outlevelled the zone lists the ones slightly below your level instead of searching the wiki; builds start with their main tree.
- Changed: answers are easier to read: one paragraph per topic, lists with one item per line and builds with one line per talent tree.
- Added: the in-window chat can be scrolled from the addon (mouse wheel over the conversation or the arrow buttons) and each new answer is shown from its beginning.
- Added: the addon window can be resized from its bottom right corner and remembers its size; the mouse wheel over the conversation and the new arrow buttons scroll the chat drawn by the companion.
- Changed: bigger scroll arrows, faster and smooth chat scrolling, and the in-window chat box is opaque so the addon text no longer shows through.
- Added: the game data and the guide are updated with the addon: the app reads the data shipped in the addon, downloads the base it needs once and rebuilds its database in seconds, so new data no longer requires reinstalling the app.
- Changed: the app reports its activity in plain language (questions, answers, data updates) and writes technical details to a log file in %LOCALAPPDATA%\AskForever\logs.
- Changed: the AI key is set up in a window (first run and "Set up the AI"), tested before saving and applied without restarting the app.
- Added: AskForever App updates itself: it checks GitHub at start and every 6 hours, verifies the new installer, installs it silently when no question is being answered and reopens.
- Changed: the companion is now AskForever App: its own window and system tray icon, no console, new shortcuts; it installs over the previous version keeping its key and data. The addon shows a one-time notice to players of the old companion.

### Español
- Añadido: el informe de VirusTotal del instalador se enlaza desde la insignia del README y la página de seguridad y transparencia, que también explica la única detección (SecureAge, etiqueta genérica) de la 0.3.0-beta.3.
- Añadido: la copia de desarrollo se carga como AskForever (desarrollo) junto al addon público, con un aviso cuando ambos están activados.
- Añadido: el addon envía la posición de su panel de conversación y avisa al companion cuando su ventana se abre, se cierra o se mueve (para el chat dentro de la ventana).
- Añadido: chat dentro de la ventana del addon: el companion dibuja toda la conversación sobre el panel de conversación del addon y sigue a la ventana al abrirla, cerrarla o moverla; sin esa información mantiene la ventana de respuesta clásica.
- Corregido: quién da y recibe una misión se elige según tu facción (a un jugador de la Alianza lo mandaba a Entrañas), las misiones con el mismo nombre se eligen para tu facción y las ubicaciones de tu zona actual salen primero.
- Añadido: las preguntas generales sobre cómo se juega reciben los textos oficiales del juego que les corresponden (tutoriales, ayudas de la interfaz para novatos y consejos de las pantallas de carga), con su referencia.
- Añadido: las preguntas sobre dónde está el banquero, el tabernero, el subastador, el maestro de vuelo, el de establos o un instructor de profesión muestran los PNJ de esa ciudad o zona con coordenadas.
- Corregido: las zonas recomendadas para tu nivel ya no incluyen las de la otra facción.
- Añadido: los cazadores que preguntan por mascotas reciben las bestias domesticables de su zona (familia, nivel y coordenadas) vistas en el juego.
- Corregido: los textos oficiales del juego se encuentran más y mejor: cuenta el título de los tutoriales («Muerte» para «he muerto»), los tutoriales de una raza o clase solo llegan a esa raza o clase y ya no se ignoran palabras como «objetos» o «misiones».
- Corregido: una pregunta corta de seguimiento («¿y para subir de nivel, cuál?») mantiene el tema de la anterior en lugar de responder solo sobre la palabra nueva.
- Corregido: una sola palabra de la pregunta ya no elige como zona un lugar menor («cazador» elegía el barco «El Cazador del Albor»); así solo se reconocen las zonas principales.
- Añadido: secciones verificadas de la guía de principiantes, cada una con sus fuentes, para las preguntas generales: qué es WoW Forever, nivel máximo, zonas nuevas, mazmorras y bandas, la nueva raza Cielonato y las combinaciones de clase, el sistema Legacy con sus ventajas y recompensas, el preajuste de experiencia y los tipos de reino.
- Corregido: si preguntas qué mazmorra puedes hacer antes del nivel de la primera, ahora te dice cuáles serán las primeras, y ya no se sugieren mazmorras dentro de las capitales de la otra facción.
- Cambiado: la IA solo menciona las zonas para tu nivel cuando preguntas adónde ir o qué hacer, y ya no añade barrios ni edificios que no estén en los datos al decir dónde está algo.
- Añadido: guía de principiantes sobre profesiones (cuántas puedes tener, qué hace cada una, buenas combinaciones, profesiones secundarias).
- Añadido: prioridad de estadísticas de cada especialización y, verificado con el cliente del juego, el nivel del primer punto de talento (10) y cuántos ganas por nivel.
- Añadido: las preguntas sobre talentos reciben los datos exactos de WoW Forever: qué hace un talento en cada rango, su rama, los puntos que pide y su requisito, los talentos de una rama y cuáles son nuevos o han cambiado en Forever.
- Añadido: guía de principiantes sobre razas (qué clases puede ser cada raza en WoW Forever, habilidades raciales, los Cielonatos).
- Añadido: guía de principiantes sobre los primeros pasos (preajustes, campamentos, saco de dormir, apellidos, transfiguración, mando y más) y sobre viajes y monturas.
- Añadido: guías de clase para principiantes (roles, qué cambia en Forever, especialización y talentos para subir de nivel, misiones y mecánicas de clase): Cazador, Guerrero, Mago, Paladín, Sacerdote, Pícaro, Chamán, Brujo, Druida
- Añadido: guía de mazmorras para principiantes (cómo llegar a cada una, qué esperar, mecánicas clave y misiones que coger antes de entrar).
- Añadido: guía de JcJ para principiantes (modos, honor y rangos, especializaciones fuertes).
- Corregido: el Salón de los Feudales y las Ruinas de Lordaeron (mazmorras nuevas dentro de una capital) se recomiendan a las dos facciones, y sus rangos de nivel en la guía coinciden con la tabla de WoW Forever.
- Añadido: en las preguntas generales la IA elige primero, en un índice de la guía, las secciones que las responden (si falla, se usa la búsqueda por palabras); se desactiva con ASKFOREVER_GUIDE_ROUTER=0.
- Corregido: las preguntas sobre «subir de nivel» se tomaban por preguntas de viaje («ir de» dentro de «subir de nivel»); las secciones de otra raza o clase solo se usan si la pregunta la nombra; los seguimientos que empiezan por «pero» o «entonces» mantienen el tema; la IA da las recomendaciones de la guía con su motivo; la cadena del saco de dormir paso a paso y qué mascota elegir como cazador para subir.
- Corregido: las secciones elegidas por la IA van primero aunque la búsqueda por palabras ya las hubiera encontrado (podían quedar recortadas), «¿cuándo podré ir a caballo?» ya no se toma por un viaje y las misiones de una sola palabra («¡Atención!») solo se reconocen si la pregunta habla de misiones.
- Cambiado: la IA da los datos directamente sin decir de dónde salen («según la guía»).
- Corregido: el enrutador de la guía tiene sitio para los identificadores largos de sección y más tiempo para responder (se cortaban y recurría a la búsqueda por palabras).
- Corregido: las secciones de la guía llegan a la IA con su título y completas (el bloque de datos de las respuestas de la guía es el doble de largo), así que las builds ya no salen cortadas ni mezcladas; ya no se busca en la wiki cuando una sección de la guía responde, y dejan de colarse talentos de otras versiones del juego.
- Cambiado: la IA da las builds completas con todos sus rangos, sabe cuántos puntos de talento tienes a tu nivel (y se detiene ahí cuando preguntas qué deberías tener), responde a preguntas sobre otras clases y no completa las builds con talentos de otras versiones del juego.
- Corregido: las secciones de builds y rutas de talentos dicen para qué son (bandas, mazmorras, JcJ o subida), así que la IA ya no dice que no tiene la build de banda cuando sí la tiene.
- Añadido: si preguntas qué misiones hay en una zona (o aquí) para tu nivel, se listan con quién las da y dónde; si preguntas por un barco sin nombrar el puerto, se listan los barcos, zepelines y tranvías conocidos; ante una pregunta ambigua la IA pregunta a qué te refieres en lugar de decir que no lo sabe.
- Corregido: las respuestas largas (builds completas, «dime todo») ya no se cortan a 900 caracteres; la IA ya no empieza las respuestas con la etiqueta interna de los datos; «¿hay más opciones?» mantiene el tema de la pregunta anterior; si preguntas qué misiones hay aquí y ya has superado la zona, se listan las que están algo por debajo de tu nivel en vez de buscar en la wiki; las builds empiezan por su rama principal.
- Cambiado: las respuestas son más fáciles de leer: un párrafo por tema, listas con un elemento por línea y builds con una línea por rama de talentos.
- Añadido: el chat dentro de la ventana se puede desplazar desde el addon (rueda del ratón sobre la conversación o botones de flecha) y cada respuesta nueva se muestra desde su principio.
- Añadido: la ventana del addon se puede redimensionar desde la esquina inferior derecha y recuerda su tamaño; la rueda del ratón sobre la conversación y los nuevos botones de flecha desplazan el chat que dibuja el companion.
- Cambiado: flechas de desplazamiento más grandes, desplazamiento del chat más rápido y suave, y el cuadro del chat es opaco para que no se transparente el texto del addon.
- Añadido: los datos del juego y la guía se actualizan con el addon: la app lee los datos que trae el addon, descarga una vez la base que necesita y reconstruye su base en segundos, así que los datos nuevos ya no requieren reinstalar la app.
- Cambiado: la app informa de su actividad en lenguaje sencillo (preguntas, respuestas, actualizaciones de datos) y guarda los detalles técnicos en un registro en %LOCALAPPDATA%\AskForever\logs.
- Cambiado: la clave de la IA se configura en una ventana (al primer arranque y con «Configurar IA»), se prueba antes de guardarla y se aplica sin reiniciar la app.
- Añadido: AskForever App se actualiza sola: comprueba GitHub al arrancar y cada 6 horas, verifica el instalador nuevo, lo instala en silencio cuando no hay una pregunta en curso y vuelve a abrirse.
- Cambiado: el companion ahora es AskForever App: ventana propia e icono en la bandeja del sistema, sin consola y con accesos directos nuevos; se instala encima de la versión anterior conservando la clave y los datos. El addon muestra un aviso único a quien use el companion anterior.

## [0.3.0-beta.4] - 2026-11-15

Fix for the position of the answer window. / Corrección de la posición de la ventana de respuesta.

### English
- Fixed: since 0.3.0-beta.3 the answer window appeared in the top-left corner instead of on the right, over the pixel strip, so a new question asked while it was visible could be lost.

### Español
- Corregido: desde la 0.3.0-beta.3 la ventana de respuesta aparecía en la esquina superior izquierda en vez de a la derecha, encima de la tira de píxeles, y una pregunta nueva hecha mientras se veía podía perderse.

## [0.3.0-beta.3] - 2026-11-15

Quest questions now include where their objective items come from. / Las preguntas de misión ahora incluyen de dónde salen sus objetos objetivo.

### English
- Fixed: questions about a quest now include where its objective items come from (which NPC drops them, with zone, coordinates and drop rate; vendors; quest rewards).
- Fixed: quest questions also include the world objects (chests, crates, plants...) that give the objective items and where the creatures of kill quests are, with zone and coordinates.
- Added: the addon sends the ID of each active quest; same-name quests are resolved with your quest log; questions that refer to an active quest without its name ('who drops the book?', 'where are those kobolds?') use that quest's data when the match is clear.
- Fixed: the answer overlay no longer flashes or takes the focus from the game when it starts or restarts, and it hides while the game is minimized or in the background.

### Español
- Corregido: las preguntas sobre una misión ahora incluyen de dónde salen sus objetos objetivo (qué PNJ los suelta, con zona, coordenadas y probabilidad; vendedores; recompensas de misión).
- Corregido: las preguntas de misión también incluyen los objetos del mundo (cofres, cajas, plantas...) que dan los objetos objetivo y dónde están las criaturas de las misiones de matar, con zona y coordenadas.
- Añadido: el addon envía el ID de cada misión activa; las misiones con el mismo nombre se resuelven con tu registro de misiones; las preguntas que se refieren a una misión activa sin nombrarla ('¿quién suelta el libro?', '¿dónde están esos kobolds?') usan sus datos cuando la coincidencia es clara.
- Corregido: la ventana de respuesta ya no parpadea ni roba el foco al juego al iniciarse o reiniciarse, y se oculta mientras el juego está minimizado o en segundo plano.

## [0.3.0-beta.2] - 2026-11-15

Welcome and help window with the setup steps and links. / Ventana de bienvenida y ayuda con los pasos de instalación y los enlaces.

### English
- Added: welcome window on first login that explains the companion, the free Gemini key and the setup links, with Copy buttons.
- Added: help window from the '?' button in the main window and from '/af help'.
- Added: the addon download includes README.txt and the installation guides and the security and data transparency report (docs/).

### Español
- Añadido: ventana de bienvenida en el primer inicio de sesión que explica el companion, la clave gratuita de Gemini y los enlaces de instalación, con botones Copiar.
- Añadido: ventana de ayuda desde el botón '?' de la ventana principal y desde '/af help'.
- Añadido: la descarga del addon incluye README.txt y las guías de instalación y el informe de seguridad y transparencia de datos (docs/).

## [0.3.0-beta.1] - 2026-11-14

First functional public beta: the addon on CurseForge and the companion installer on GitHub Releases. / Primera beta pública funcional: el addon en CurseForge y el instalador del companion en GitHub Releases.

### English
- Added: the companion supports several OpenAI-compatible cloud providers (Gemini, Groq, Mistral, Cerebras, OpenRouter), one key and one model per provider, with `providers`, `list-models` and `--provider` / `--model` options.
- Added: verified game data from a local wowdata database (read-only): quests (giver, turn-in, objectives), NPC locations, class trainer spells and trainers, dungeon entrances, flight points, talent trees and item sources are detected in the question and passed to the AI, which must use only that data and say when something is missing. Tested with 19 questions: from 3 correct answers without data to about 16 with data. Developer only for now (the database is not distributed). Commands: `data-check`, `--no-data`, `--show-data`.
- Added: more verified data from wowdata: zone level ranges and zones for your level, dungeon levels, bosses and dungeons for your level, experience to the next level, quest experience and objectives, item drops from `v_botin`, flights from a place with their cost and transports. Travel route questions are answered as missing data until the routes are in the database (never searched on the internet). Second battery of 15 questions: 14 with correct data, the route one answered honestly as missing.
- Added: WoW Forever dungeon level ranges provided by the maintainer (`companion/askforever/data/forever_dungeon_levels.json`, including Scarlet Monastery wings and Stratholme entrances); they take precedence over the client values.
- Added: conversation memory: questions asked while the addon window stays open are chained (the addon sends a conversation number that changes when the window is closed after asking); follow-up questions reuse the data of the previous one.
- Added: level panorama in every question (zones and dungeons for your level), removing the zones the player excludes.
- Changed: more useful prompt: concrete recommendations from the data, one sentence for what is missing, never refers to guides and never names places that are not in the data.
- Fixed: the answer overlay no longer flashes over the game (it hides with transparency instead of unmapping).
- Added: travel routes computed from the database: flights and transports from wowdata (including trips recorded in the game, such as the Stormwind - Darkshore boat) plus the Deeprun Tram confirmed by the maintainer; the fastest route is described step by step with an approximate time; questions like "is there a boat from X to Y?" are answered from the data. Routes and transports never come from the internet or from the model's general knowledge.
- Added: warcraft.wiki.gg fallback when the database has no data for the question (not for travel): short English searches, preference for WoW Forever pages, answers say "according to the wiki" and show the sources; if neither the database nor the wiki has it, the AI says so without naming places. `--no-web` disables it.
- Fixed: profession questions (fishing, first aid, skinning...) no longer trigger the class spells or trainers.
- Changed: answers follow the language of the question; default temperature 0.2 (`ASKFOREVER_TEMPERATURE`).
- Added: guide to create free keys for each provider with verified links (`docs/API_KEYS.md`).
- Added: model comparison tool `bench`: runs 10 fixed WoW questions (zones, routes, class, dungeons, quests, honesty traps and an English question) against several providers/models and writes a Markdown + JSON report with latencies, errors and full answers to score by hand.
- Fixed: "and from here to X?" questions now compute the route from the player's position (before, no route was computed and the AI could make it up); travel questions whose places are not recognised are reported as missing data.
- Added: when the route starts somewhere else, the answer also gives the route from the player's position to that starting point (for example, the tram from Ironforge to Stormwind before the Darkshore boat).
- Added: routes take the known flight points into account when the addon sends them (`ctx.fp`, TaxiNodes IDs): flights only between known points, a note with the faster route once the missing points are discovered, and a reminder to discover the flight point at the destination. Without that list, the answer names the flight points the route uses and says how to register them.
- Fixed: generic words in place names ("valle", "bosque"...) no longer match other places by prefix (Coldridge Valley resolved to Astranaar); when origin and destination are in the same zone the answer says to walk; without the list of known flight points, a route without flights is also given.
- Fixed: capital city flight points are shown with the city name only (the client calls them "Stormwind, Elwynn" or "Ironforge, Dun Morogh", which made the AI say there was a flight point in Elwynn Forest); the walking note no longer says that two different zones are the same one.
- Fixed: the answer overlay could hang while the companion kept answering in the console. It now runs in a watched child process: if it stops responding for 10 s or dies, it is restarted and shows the last state again (at most 5 restarts every 5 minutes). Overlay errors are written to `addon/AskForever/dev/companion.log` (development folder, ignored by git and excluded from the release). `run --overlay-inprocess` keeps the old behaviour for diagnosis.
- Fixed: when the data did not answer the exact question (for example, whether dual specialization exists), the AI could state or deny game features from its general knowledge of other WoW versions. A new rule makes it say it does not have that information.
- Fixed: the packaged program could not read, save or delete the API key in the Windows Credential Manager (keyring did not find its backend inside the PyInstaller build), so it asked for the key again and the uninstaller left it behind. The release build now runs a smoke test of the packaged program that saves, reads and deletes a test key.
- Fixed: uninstalling while AskForever was open left the program and data folders behind; the uninstaller now closes it first and removes both folders completely, and updating closes it too. The installation guide shows the Windows SmartScreen warning.
- Fixed (development only): the report window did not take keyboard focus for the note.
- Changed: the experimental slot diagnostics (`/af slotprobe`, `/af slottest`) moved to the development folder; they are not part of the public addon.
- Added: Windows packaging built only on GitHub Actions: the companion as a PyInstaller folder app (no UPX) with a per-user Inno Setup installer (no administrator rights, Start menu shortcut, uninstaller that runs `uninstall --yes`). Pushing a `v*` tag builds, tests, hashes (SHA-256), attests the provenance and publishes the release with the installer and the addon zip; changes in `dev` only build test artifacts.
- Added: simple first run: starting the companion without arguments (double click) runs it; if there is no API key, a console wizard opens the key guide, asks for the key, tests it and saves it in the Windows Credential Manager (`setup` runs it again). `uninstall` removes the saved keys, the companion's data folder and the helper slot addons (never follows links outside their folders; `--addon` also removes the addon).
- Added: game data downloader in the companion: downloads the game database published on GitHub Releases (`data-YYYY.MM.DD`), checks its SHA-256 and integrity and installs it atomically in `%LOCALAPPDATA%\AskForever\data` (keeping a backup); `update-data` command and `--no-update` option. The developer's own wowdata database is never replaced. Next: updates through the CurseForge addon.
- Added: public continuous integration on GitHub Actions: companion tests on Windows, CodeQL code scanning and Dependabot updates, with CI, CodeQL, license and release badges and links to the security page in the README.
- Added: security and transparency page (`docs/SECURITY_TRANSPARENCY.md`, `docs/SEGURIDAD_TRANSPARENCIA.md`), checked against the code: what the companion does and never does, every network connection, the data sent to the AI, the files and settings it touches, how to verify it and why Windows may show a warning. `SECURITY.md` explains how to report a security problem.
- Fixed: answers based on the (English) wiki used English names in Spanish answers. The AI now receives the official Spanish names found in wowdata for the names in the wiki excerpts (for example "Well Fed = Bien alimentado") and must use them; untranslated names are quoted and marked as English.
- Added (development only): "Informe" button in the AskForever window that sends a report message (with the note typed in the box) to the companion, which writes a plain text file in `addon/AskForever/dev/informes/` with the last question, player context, data given to the AI, model, time and answer. The button opens its own window with the last question and a box to describe what is wrong (an empty report asks for confirmation). The window also lists the open reports, each with a Close button that asks the companion to delete its file (strictly validated id, only inside the reports folder). It lives in `addon/AskForever/dev/`, which `build-release.ps1` leaves out of the public zip (and fails if anything from it slips in).
- Added (addon): known flight points are saved per character when a flight master's map is opened and sent with each question (`fp`); a chat line confirms new points. The last reading is kept in `AskForeverDB.flightsDebug` to check which taxi API the client has.

### Español
- Añadido: el companion admite varios proveedores de IA en la nube compatibles con OpenAI (Gemini, Groq, Mistral, Cerebras, OpenRouter), con una clave y un modelo por proveedor, y los comandos `providers`, `list-models` y las opciones `--provider` / `--model`.
- Añadido: datos de juego verificados desde una base local de wowdata (solo lectura): misiones (quién la da, dónde se entrega, objetivos), posiciones de PNJ, hechizos de instructor e instructores, entradas de mazmorras, puntos de vuelo, ramas de talentos y origen de objetos se detectan en la pregunta y se pasan a la IA, que debe usar solo esos datos y decir cuándo falta algo. Probado con 19 preguntas: de 3 respuestas correctas sin datos a unas 16 con datos. Por ahora solo para desarrollo (la base no se distribuye). Comandos: `data-check`, `--no-data`, `--show-data`.
- Añadido: más datos verificados de wowdata: niveles de zona y zonas para tu nivel, nivel, jefes y mazmorras para tu nivel, experiencia hasta el siguiente nivel, experiencia y objetivos de misión, botín desde `v_botin`, vuelos desde un lugar con su coste y transportes. Las preguntas de rutas de viaje se responden como dato ausente hasta que las rutas estén en la base (nunca se buscan en internet). Segunda batería de 15 preguntas: 14 con datos correctos y la de ruta respondida honestamente como ausente.
- Añadido: rangos de nivel de las mazmorras de WoW Forever facilitados por el mantenedor (`companion/askforever/data/forever_dungeon_levels.json`, con las alas del Monasterio Escarlata y las entradas de Stratholme); mandan sobre los valores del cliente.
- Añadido: memoria de conversación: las preguntas hechas mientras la ventana del addon sigue abierta se encadenan (el addon manda un número de conversación que cambia al cerrarla tras preguntar); las preguntas de seguimiento reutilizan los datos de la anterior.
- Añadido: panorama del nivel en cada pregunta (zonas y mazmorras para tu nivel), quitando las zonas que el jugador descarta.
- Cambiado: prompt más útil: recomendaciones concretas con los datos, una frase para lo que falta, nunca remite a guías ni nombra lugares que no estén en los datos.
- Corregido: el overlay de respuesta ya no parpadea sobre el juego (se oculta con transparencia en lugar de desmapearse).
- Añadido: rutas de viaje calculadas con la base: vuelos y transportes de wowdata (incluidos los viajes grabados en el juego, como el barco Ventormenta - Costa Oscura) más el Tranvía Subterráneo confirmado por el mantenedor; la ruta más rápida se describe paso a paso con un tiempo aproximado; preguntas como «¿hay barco de X a Y?» se responden con los datos. Las rutas y los transportes nunca salen de internet ni del conocimiento general del modelo.
- Añadido: respaldo de warcraft.wiki.gg cuando la base no tiene datos para la pregunta (no para viajes): búsquedas cortas en inglés, preferencia por las páginas de WoW Forever, las respuestas dicen «según la wiki» y muestran las fuentes; si ni la base ni la wiki lo tienen, la IA lo dice sin nombrar lugares. `--no-web` lo desactiva.
- Corregido: las preguntas de profesiones (pesca, primeros auxilios, desuello…) ya no activan los hechizos ni los instructores de la clase.
- Cambiado: las respuestas siguen el idioma de la pregunta; temperatura por defecto 0,2 (`ASKFOREVER_TEMPERATURE`).
- Añadido: guía para crear claves gratuitas de cada proveedor con enlaces comprobados (`docs/CLAVES_API.md`).
- Añadido: herramienta de comparación de modelos `bench`: lanza 10 preguntas fijas de WoW (zonas, rutas, clase, mazmorras, misiones, trampas de honestidad y una pregunta en inglés) a varios proveedores y modelos y genera un informe Markdown + JSON con latencias, errores y respuestas completas para puntuar a mano.
- Corregido: las preguntas del tipo «¿y de aquí a X?» calculan la ruta desde la posición del jugador (antes no se calculaba y la IA podía inventársela); las preguntas de viaje cuyos lugares no se reconocen se marcan como dato ausente.
- Añadido: cuando la ruta empieza en otro sitio, la respuesta da también la ruta desde la posición del jugador hasta ese origen (por ejemplo, el tranvía de Forjaz a Ventormenta antes del barco a Costa Oscura).
- Añadido: las rutas tienen en cuenta los puntos de vuelo conocidos cuando el addon los envía (`ctx.fp`, IDs de TaxiNodes): vuelos solo entre puntos conocidos, aviso con la ruta más rápida cuando se descubran los que faltan y recordatorio de descubrir el punto de vuelo del destino. Sin esa lista, la respuesta nombra los puntos de vuelo que usa la ruta y explica cómo registrarlos.
- Corregido: las palabras genéricas de los nombres de lugar («valle», «bosque»…) ya no casan por prefijo con otros lugares (el Valle de Crestanevada salía como Astranaar); si origen y destino están en la misma zona, la respuesta dice que se va a pie; sin la lista de puntos de vuelo conocidos, se da también la ruta sin vuelos.
- Corregido: los puntos de vuelo de las capitales se muestran solo con el nombre de la ciudad (el cliente los llama «Ventormenta, Elwynn» o «Forjaz, Dun Morogh» y la IA decía que había vuelo en el Bosque de Elwynn); la nota de ir a pie ya no dice que dos zonas distintas son la misma.
- Corregido: el overlay de respuesta podía colgarse mientras el companion seguía respondiendo en la consola. Ahora va en un proceso hijo vigilado: si deja de responder 10 s o muere, se reinicia y vuelve a mostrar el último estado (como mucho 5 reinicios cada 5 minutos). Los errores del overlay se escriben en `addon/AskForever/dev/companion.log` (carpeta de desarrollo, ignorada por git y fuera de la release). `run --overlay-inprocess` mantiene el comportamiento anterior para diagnosticar.
- Corregido: cuando los datos no respondían justo a lo preguntado (por ejemplo, si existe la doble especialización), la IA podía afirmar o negar funciones del juego con lo que sabe de otras versiones de WoW. Una regla nueva hace que diga que no tiene ese dato.
- Corregido: el programa empaquetado no podía leer, guardar ni borrar la clave en el Administrador de credenciales de Windows (keyring no encontraba su almacén dentro del empaquetado de PyInstaller), así que volvía a pedir la clave y el desinstalador no la borraba. La compilación de la versión ejecuta ahora una prueba del programa empaquetado que guarda, lee y borra una clave de prueba.
- Corregido: desinstalar con AskForever abierto dejaba las carpetas del programa y de los datos; ahora el desinstalador lo cierra antes y borra las dos carpetas por completo, y al actualizar también lo cierra. La guía de instalación muestra el aviso de Windows SmartScreen.
- Corregido (solo desarrollo): la ventana de informe no daba el foco del teclado al cuadro de la nota.
- Cambiado: los diagnósticos experimentales de slots (`/af slotprobe`, `/af slottest`) pasan a la carpeta de desarrollo; no forman parte del addon público.
- Añadido: empaquetado para Windows compilado solo en GitHub Actions: el companion como programa en carpeta de PyInstaller (sin UPX) con un instalador de Inno Setup por usuario (sin permisos de administrador, acceso en el menú Inicio y desinstalador que ejecuta `uninstall --yes`). Una etiqueta `v*` compila, prueba, calcula los SHA-256, atestigua la procedencia y publica la versión con el instalador y el zip del addon; los cambios en `dev` solo compilan artefactos de prueba.
- Añadido: primer arranque sencillo: abrir el companion sin argumentos (doble clic) lo pone en marcha; si no hay clave de la API, un asistente en la consola abre la guía, pide la clave, la prueba y la guarda en el Administrador de credenciales de Windows (`setup` lo repite). `uninstall` borra las claves guardadas, la carpeta de datos del companion y los addons auxiliares de slots (nunca sigue enlaces fuera de sus carpetas; `--addon` borra también el addon).
- Añadido: descargador de datos del juego en el companion: descarga la base publicada en GitHub Releases (`data-AAAA.MM.DD`), comprueba su SHA-256 y su integridad y la instala de golpe en `%LOCALAPPDATA%\AskForever\data` (con copia de seguridad); comando `update-data` y opción `--no-update`. La base de wowdata del desarrollador nunca se sustituye. Siguiente paso: actualizaciones a través del addon de CurseForge.
- Añadido: integración continua pública en GitHub Actions: pruebas del companion en Windows, análisis del código con CodeQL y actualizaciones de Dependabot, con etiquetas de CI, CodeQL, licencia y versión y enlaces a la página de seguridad en el README.
- Añadido: página de seguridad y transparencia (`docs/SECURITY_TRANSPARENCY.md`, `docs/SEGURIDAD_TRANSPARENCIA.md`), comprobada contra el código: qué hace el companion y qué no hace nunca, todas las conexiones de red, los datos que se envían a la IA, los archivos y ajustes que toca, cómo comprobarlo y por qué Windows puede mostrar un aviso. `SECURITY.md` explica cómo avisar de un problema de seguridad.
- Corregido: las respuestas basadas en la wiki (en inglés) usaban nombres en inglés en respuestas en español. La IA recibe ahora los nombres oficiales en español que hay en wowdata para los nombres de los extractos de la wiki (por ejemplo «Well Fed = Bien alimentado») y debe usarlos; los que no tienen traducción van entre comillas indicando que son el nombre en inglés.
- Añadido (solo desarrollo): botón «Informe» en la ventana de AskForever que envía al companion un mensaje de informe (con la nota escrita en la caja); el companion escribe un archivo de texto plano en `addon/AskForever/dev/informes/` con la última pregunta, el contexto del jugador, los datos que recibió la IA, el modelo, el tiempo y la respuesta. El botón abre una ventana propia con la última pregunta y un cuadro para escribir qué está mal (un informe vacío pide confirmación). La ventana también lista los informes abiertos, cada uno con un botón Cerrar que pide al companion borrar su archivo (identificador validado y solo dentro de la carpeta de informes). Vive en `addon/AskForever/dev/`, que `build-release.ps1` deja fuera del zip público (y falla si se cuela algo).
- Añadido (addon): los puntos de vuelo conocidos se guardan por personaje al abrir el mapa de un maestro de vuelo y se envían con cada pregunta (`fp`); una línea en el chat confirma los nuevos. La última lectura queda en `AskForeverDB.flightsDebug` para comprobar qué API de taxi trae el cliente.

## [0.2.0-beta.1] - 2026-11-14

Milestone 2: the first end-to-end answer. Tested in WoW Forever (1920x1080, borderless window): the pixel strip is read with 0 errors and a question reaches the companion in about 200 ms. Minor bump: new functionality, backwards compatible. Developer preview: the companion runs from source (no installer yet, planned for 0.4.0) and is not yet part of the CurseForge package.

### English
- Added: the chat window now also sends the question and the character context to the companion through a strip of colored blocks in the top-left corner of the screen (pixel-exact, CRC-32, paginated, only outside combat). No input is simulated and no memory is read.
- Added: companion (Python): finds the game window, captures and decodes the strip, reassembles messages without duplicates, asks Google Gemini and shows the answer in a click-through overlay that never takes focus. Commands: `run`, `listen`, `ask`, `overlay-demo`, `set-key`, `test-key`.
- Added: OpenAI-compatible provider layer with retries on rate limits and readable errors; the key is kept in the Windows Credential Manager. Default model `gemini-3.5-flash-lite` (about 1 s); `gemini-3.8-flash`, `3.7-flash` and `flash-latest` did not answer within 60 s on the free plan when tested.
- Added: `/af pattern` (shows a test pattern for 10 seconds) and `/af selftest` (checks the protocol) as diagnostics.
- Added: step-by-step guide to create and store a free Google Gemini key (`docs/GEMINI_KEY.md`).
- Known limits: no memory between questions, no profession/talent/inventory data and no verified game data yet, so answers can be wrong; answers appear in an overlay, not in the addon window.

### Español
Milestone 2: la primera respuesta de extremo a extremo. Probado en WoW Forever (1920x1080, ventana sin bordes): la tira de píxeles se lee con 0 errores y una pregunta llega al companion en unos 200 ms. Subida menor: funcionalidad nueva, compatible. Versión para desarrolladores: el companion se ejecuta desde el código (aún sin instalador, previsto para la 0.4.0) y todavía no forma parte del paquete de CurseForge.

- Añadido: la ventana de chat ahora también envía la pregunta y el contexto del personaje al companion con una tira de bloques de color en la esquina superior izquierda de la pantalla (píxel exacto, CRC-32, paginada, solo fuera de combate). No simula teclas ni lee memoria.
- Añadido: companion (Python): localiza la ventana del juego, captura y decodifica la tira, reensambla los mensajes sin duplicados, pregunta a Google Gemini y muestra la respuesta en un overlay que deja pasar los clics y nunca roba el foco. Comandos: `run`, `listen`, `ask`, `overlay-demo`, `set-key`, `test-key`.
- Añadido: capa de proveedor compatible con OpenAI con reintentos ante límites y errores legibles; la clave se guarda en el Administrador de credenciales de Windows. Modelo por defecto `gemini-3.5-flash-lite` (alrededor de 1 s); `gemini-3.8-flash`, `3.7-flash` y `flash-latest` no respondieron en 60 s en el plan gratuito durante la prueba.
- Añadido: `/af pattern` (muestra un patrón de prueba 10 segundos) y `/af selftest` (comprueba el protocolo) como diagnóstico.
- Añadido: guía paso a paso para crear y guardar una clave gratuita de Google Gemini (`docs/CLAVE_GEMINI.md`).
- Límites conocidos: sin memoria entre preguntas, sin datos de profesiones, talentos ni inventario y sin datos de juego verificados, así que las respuestas pueden ser erróneas; la respuesta sale en un overlay, no en la ventana del addon.

## [0.1.0-beta.1] - 2026-11-13

First working addon (milestone 1). Tested in WoW Forever (interface 16001); not published on CurseForge yet. Minor bump: first functionality, backwards compatible.

### English
- Added: chat window in the native Lorewake/FishForever style (portrait frame, dark panels), opened with `/af`, `/askforever`, a configurable keybind or the minimap button.
- Added: character context collection (level, race, class, faction, zone, subzone, coordinates, active quests with level).
- Added: **Copy prompt** button: builds a ready-to-use prompt with that context and shows it selected for `Ctrl+C`.
- Added: draggable minimap button (`/af minimap` shows or hides it), `/af help` and `/af reset`.
- Added: English and Spanish locales (`esES` also for `esMX`).
- Added: own icon (speech bubble with a question mark) for the window portrait, minimap button and addon list; `scripts/make-icons.py` regenerates it.
- Added: `scripts/build-release.ps1` (builds the CurseForge zip, checks the `.toc`) and `docs/CURSEFORGE.md` (page texts and checklist).

### Español
Primer addon funcional (milestone 1). Probado en WoW Forever (interfaz 16001); todavía sin publicar en CurseForge. Subida menor: primera funcionalidad, compatible.

- Añadido: ventana de chat con el estilo nativo de Lorewake/FishForever (marco con retrato, paneles oscuros), que se abre con `/af`, `/askforever`, un atajo configurable o el botón del minimapa.
- Añadido: recogida del contexto del personaje (nivel, raza, clase, facción, zona, subzona, coordenadas, misiones activas con nivel).
- Añadido: botón **Copiar prompt**: construye un prompt listo para usar con ese contexto y lo muestra seleccionado para `Ctrl+C`.
- Añadido: botón de minimapa arrastrable (`/af minimap` lo muestra u oculta), `/af help` y `/af reset`.
- Añadido: idiomas inglés y español (`esES` también para `esMX`).
- Añadido: icono propio (bocadillo con interrogación) para el retrato de la ventana, el botón del minimapa y la lista de addons; `scripts/make-icons.py` lo regenera.
- Añadido: `scripts/build-release.ps1` (genera el zip para CurseForge y comprueba el `.toc`) y `docs/CURSEFORGE.md` (textos de la página y lista de comprobación).

## [0.0.1] - 2026-11-13

First release: documentation only, no addon or companion yet.

### English
- Added: README, ROADMAP, TODO, installation guides (EN/ES), CC BY-NC 4.0 license and folder structure.
- Added: `scripts/dev-link.ps1` to symlink the addon into the game client during development.

### Español
Primera publicación: solo documentación, sin addon ni companion todavía.

- Añadido: README, ROADMAP, TODO, guías de instalación (EN/ES), licencia CC BY-NC 4.0 y estructura de carpetas.
- Añadido: `scripts/dev-link.ps1` para enlazar el addon al cliente durante el desarrollo.
