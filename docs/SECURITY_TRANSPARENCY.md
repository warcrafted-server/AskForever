# Security and transparency

*Versión en español: [SEGURIDAD_TRANSPARENCIA.md](SEGURIDAD_TRANSPARENCIA.md)*

AskForever has two parts: the **addon** (runs inside the game, like any other addon) and the
**companion** (a small Windows program that talks to the AI). This page explains exactly what
the companion does and what it never does, so you can decide with all the facts. Everything
here can be checked in the source code of this repository.

## In one minute

- It **looks at a small strip of the game window** (512 × 32 pixels in the top-left corner)
  where the addon draws your question as coloured pixels. Nothing else on your screen.
- It sends your question and some character context to **the AI provider you choose**, and
  can look things up on **warcraft.wiki.gg**. It connects to nothing else.
- It **never** reads the game's memory, injects anything into the game, or presses keys or
  moves the mouse for you.
- Your API key is stored in the **Windows Credential Manager**, never in a plain file.
- No accounts, no telemetry, no servers of ours: there is no AskForever server at all.

## What the companion does

| What | Details | Where in the code |
|---|---|---|
| Finds the game window | Lists the visible windows and checks which one belongs to `Wow.exe` (it asks Windows for the process name only, with the minimum permission `PROCESS_QUERY_LIMITED_INFORMATION`). | `companion/askforever/capture/window.py` |
| Reads the pixel strip | Captures only a 512 × 32 pixel area of the game window's top-left corner, about 30 times per second, to read the message the addon draws there. Images stay in memory and are never saved to disk. | `companion/askforever/capture/grabber.py` |
| Answers with AI | Sends your question, the conversation so far and your character context to the AI provider you configured (see the table below). | `companion/askforever/engine/`, `companion/askforever/providers/openai_compat.py` |
| Looks things up on the wiki | When its game data has no answer (never for travel routes), it searches warcraft.wiki.gg with short search terms. You can turn it off with `--no-web`. | `companion/askforever/web/wiki.py` |
| Shows the answer | Opens a small always-on-top window over the game that ignores clicks (it never takes focus or input). | `companion/askforever/overlay/` |

### What is sent to the AI provider

Only what is needed to answer: your **question**, the previous questions and answers of the
same conversation, and the **character context** the addon collects: level, race, class,
faction, zone and sub-zone, map coordinates, the titles and levels of the quests in your log
and the IDs
of the flight points you know. **Never** your account, character name, realm, chat, friends
or anything outside the game.

The AI provider receives this data under its own privacy terms. Free tiers may use the data
to improve their models: check your provider's terms (links in the API key guide).

### Network connections (complete list)

| Destination | When | Why |
|---|---|---|
| The AI provider you configured: Google Gemini (`generativelanguage.googleapis.com`), Groq (`api.groq.com`), Mistral (`api.mistral.ai`), Cerebras (`api.cerebras.ai`) or OpenRouter (`openrouter.ai`) | Each time you ask something | To get the answer |
| `warcraft.wiki.gg` | Only when the game data has no answer (and never with `--no-web`) | To look up information |
| GitHub (`api.github.com` and GitHub's download servers) | When the companion starts (never with `--no-update`) | To check whether there is newer game data and, if so, download it from this project's releases (the file's SHA-256 is checked before using it) |

Only the AI provider you chose is contacted, plus the two above. There are no other
connections: no analytics, no advertising, and the program itself does not update on its own.
The provider list is in `companion/askforever/config.py`; the data download is in
`companion/askforever/updates.py`.

### Files and settings it touches

| Location | What | When |
|---|---|---|
| Windows Credential Manager, entry `AskForever` | Your API key | When you save the key |
| `Interface\AddOns\AskForever` (inside your game folder) | The addon itself and its saved settings (`WTF\...\SavedVariables\AskForever.lua`), managed by the game | When you install the addon |
| `%LOCALAPPDATA%\Programs\AskForever` | The program itself, placed there by the installer (no administrator rights) | When you install it |
| `%LOCALAPPDATA%\AskForever\data` | The game database downloaded from GitHub (`wow.sqlite`, about 100 MB, plus a backup of the previous version and `version.json`) | First start and when there is newer data |
| `%LOCALAPPDATA%\AskForever\companion.log` | Error log of the answer window (rotated, at most about 4 MB). It contains no API keys | While the companion runs |
| `Interface\AddOns\AskForever_Slot*` | *Planned (next milestone):* small helper addons that carry the answer back into the game window | — |

Uninstalling removes all of the above except the addon, which you remove like any other addon (see below).

## What the companion never does

- It does **not** read or write the game's memory, and does not inject code or overlays into
  the game process.
- It does **not** simulate keyboard or mouse input, and does not type in the chat.
- It does **not** capture anything outside that 512 × 32 strip, and does not save screenshots.
- It does **not** send data to us or to anyone other than the AI provider you chose and
  warcraft.wiki.gg.
- It does **not** run in the background when you close it, and does not start with Windows.

These are design rules of the project (see the architecture rules in the repository), not
only promises: the code is public so anyone can check them.

## How to verify it yourself

Status of each check (we only list what really exists today):

| Check | Status |
|---|---|
| Full source code public on GitHub | Available |
| Automated tests | Available: they run on GitHub on every change (CI badge) and locally with `pytest` in `companion/` |
| Program built automatically on GitHub from the public code (never on a personal computer) | Available from version 0.3.0-beta.1 (see the Release workflow in Actions) |
| SHA-256 hash of each download published with the release | Available from version 0.3.0-beta.1 (`.sha256` files and release notes) |
| Build provenance attestation (`gh attestation verify <file> --repo warcrafted-server/AskForever`) | Available from version 0.3.0-beta.1, also for the game data |
| VirusTotal scan linked from each release | Available from version 0.3.0-beta.3: [installer report](https://www.virustotal.com/gui/file/882e541ae884519ebb20d147770122a857fb81c2f1f9ae8e477c12eb5ecfa077). One engine flags it (see below) |
| Automatic code scanning (CodeQL) and dependency updates (Dependabot) | Available (see the badges in the README) |

## Antivirus detections

We publish the VirusTotal report of each installer, including detections we believe are false positives.

- **0.3.0-beta.3:** one engine, **SecureAge**, flags the installer with the generic label "Malicious" (no malware family named); the other engines report nothing. The file is the one built on GitHub (its SHA-256 matches the `.sha256` published with the release). Unsigned installers built with PyInstaller and Inno Setup are often flagged this way by heuristic engines. We report it to the vendor as a false positive and will update this page with the answer.

If an antivirus flags AskForever, you can check the hash and the build provenance with the steps above, read the source code, or build it yourself.

## Why Windows may show a warning

The program is not distributed through the Microsoft Store and is not signed with a paid
certificate, so Windows SmartScreen may say it "protected your PC" from an unrecognised app.
This warning means "Windows does not know this program yet", not "this program is
dangerous". You can check it with the steps above and then choose **More info → Run anyway**.
If you prefer not to, you can build it yourself from the source code.

## Uninstalling without leftovers

The installer adds AskForever to Windows "Installed apps". Uninstalling it (Settings > Apps >
AskForever > Uninstall) removes the program and its shortcuts, the saved API keys, the
downloaded game data, the log and the helper slot addons. The `AskForever` addon itself is
removed from the CurseForge app or by deleting its folder, like any other addon.

## Reporting a security problem

See [SECURITY.md](../SECURITY.md).
