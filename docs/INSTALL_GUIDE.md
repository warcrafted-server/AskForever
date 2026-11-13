# AskForever installation guide (EN)

**[Versión en español](GUIA_INSTALACION.md)**

> 🚧 Guide for **v0.1.0-beta**, which works in the game but is not published yet (the CurseForge page does not exist yet, so for now the addon is installed from the repository). This guide is updated with every release. If a step does not match what you see, check the latest version on GitHub.

Estimated time: **2 minutes**, once.

## What v0.1.0 does

v0.1.0 contains only the **addon**. It collects your character's context (level, race, class, faction, zone, coordinates, active quests) and builds a ready-to-use prompt that you copy and paste into any AI chat (Gemini, ChatGPT, Claude…). Getting the answer inside the game needs the **companion**, which arrives in later versions (see the [ROADMAP](../ROADMAP.md)).

## Requirements

- WoW Forever installed.
- Nothing else for v0.1.0.

## 1. Install the addon

### Option A: CurseForge app (recommended)
1. Open the **CurseForge** app → **World of Warcraft**.
2. Make sure the **Forever** installation is selected. If it is missing, use *Scan for games* or add the `World of Warcraft\_forever_` folder manually.
3. Search for **AskForever** and click **Install**.

### Option B: manual
1. Download the `.zip` from the AskForever page on CurseForge (**Files** tab).
2. Unzip it and copy the `AskForever` folder into `World of Warcraft\_forever_\Interface\AddOns\`.
3. It must look like this: `...\AddOns\AskForever\AskForever.toc`

### Until it is on CurseForge: from GitHub
1. On the [repository page](https://github.com/warcrafted-server/AskForever) click **Code → Download ZIP** and unzip it.
2. Copy only the `addon\AskForever` folder (not the whole repository) into `World of Warcraft\_forever_\Interface\AddOns\`.
3. It must look like this: `...\AddOns\AskForever\AskForever.toc`

## 2. Start the game

If the game was open, **close it completely and start it again**: `/reload` does not detect new addons. At character select, click **AddOns** and make sure **AskForever** is enabled.

## 3. Ask your first question

1. Log in with your character.
2. Open AskForever with `/af` (or `/askforever`), or with the keybind you set in *Options → Keybindings → AddOns → AskForever*.
3. The window shows a summary of your character (level, race, class, zone). Type your question, for example: *how do I get to The Barrens?*, and press Enter. The question appears in the history with the note "Prompt ready".
4. Click **Copy prompt**. A box appears with the prompt already selected: press `Ctrl+C`.
5. Paste it into the AI chat of your choice. You do not need to say your level, faction or location: the prompt already includes them.

The minimap button opens and closes the window. Drag it to move it; `/af minimap` shows or hides it.

## Coming next: AI key

The next versions add the companion, which needs a free Google Gemini key. Step-by-step guide: [Get your free Gemini key](GEMINI_KEY.md). You do not need it for v0.1.x.

## Troubleshooting

| Problem | Fix |
|---|---|
| `/af` does nothing | AskForever is not enabled or the game was not restarted after installing. See step 2. |
| An error pops up on login | Install **BugSack** and **BugGrabber**, reproduce the error, and open a [GitHub issue](https://github.com/warcrafted-server/AskForever/issues) with the text. |
| The prompt shows the wrong zone or no quests | Open the window again after changing zone; if it persists, report it. |
| The window is lost off-screen | Run `/af reset` to restore its position (available from v0.1.0). |

## Uninstall

Uninstall it from the CurseForge app, or delete `Interface\AddOns\AskForever`. Your settings are in `WTF\Account\<account>\SavedVariables\AskForever.lua` (optional to delete).

## FAQ

**Is it free?** Yes.

**Can I get banned?** AskForever does not simulate input, read game memory or automate actions: it only displays information through the official addon API. Still, Blizzard has not stated a position on this kind of tool, so nothing can be guaranteed. Use it at your own risk.

**What data does it handle?** Your question and your character's context. In v0.1.0 nothing is sent anywhere: you decide what to paste and where.

**Does it work on Mac or Linux?** The addon works wherever the game does. The companion (future versions) will be Windows only at first.
