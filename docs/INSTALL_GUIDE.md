# AskForever installation guide (EN)

**[Versión en español](GUIA_INSTALACION.md)**

> 🚧 Living guide: updated with every release. If a step doesn't match what you see, check the latest version on GitHub.

Estimated time: **5–10 minutes**, once. After that, just open the game and ask.

---

## Contents
1. [Requirements](#1-requirements)
2. [Get your free Google Gemini key](#2-get-your-free-google-gemini-key)
3. [Install the addon](#3-install-the-addon)
4. [Install the companion](#4-install-the-companion)
5. [First-run wizard](#5-first-run-wizard)
6. [Restart WoW (first time only)](#6-restart-wow-first-time-only)
7. [Your first question](#7-your-first-question)
8. [Other AI engines (optional)](#8-other-ai-engines-optional)
9. [Troubleshooting](#9-troubleshooting)
10. [Uninstall](#10-uninstall)
11. [FAQ](#11-faq)

---

## 1. Requirements

- Windows 10 or 11.
- WoW Forever installed.
- A Google account (for the free AI key).
- The game in **"Windowed"** or **"Windowed (Fullscreen)" / borderless** mode. In **exclusive fullscreen** the companion cannot read the screen.
  - In game: `Esc` → **Options** → **Graphics** → **Display Mode** → *Windowed (Fullscreen)*.

## 2. Get your free Google Gemini key

The key is like a password that lets the companion use Google's AI. **It's free and needs no credit card.**

1. Go to **[Google AI Studio](https://aistudio.google.com/)** and sign in with your Google account.
2. If it's your first time, accept the terms of use.
3. In the left menu, click **Get API key**.
4. Click **Create API key**. If asked for a project, keep the suggested one or create a new one.
5. Copy the key (it starts with `AIza…`) using the copy button.
6. Keep it somewhere safe for now: you'll paste it in step 5.

![Create a key in Google AI Studio](img/guide-aistudio-key.png) <!-- TODO screenshot -->

**Important:**
- 🔒 **Never share or publish your key.** AskForever stores it encrypted in Windows Credential Manager.
- 🆓 The free plan has **per-minute and per-day limits**. That's plenty for normal play; if you hit them, AskForever will tell you and you can ask again shortly.
- 📄 On the free plan, Google may use request content to improve its products (depending on your region and terms). Don't put personal data in your questions.
- You can enable billing on Google for higher limits, but it is **not required**.

## 3. Install the addon

### Option A: CurseForge app (recommended)
1. Open the **CurseForge** app → **World of Warcraft**.
2. Make sure the **Forever** installation is selected. If it's missing, use *Scan for games* or add the `World of Warcraft\_forever_` folder manually.
3. Search for **AskForever** and click **Install**.

### Option B: manual
1. Download the `.zip` from the AskForever CurseForge page (**Files** tab, file marked *Forever*).
2. Unzip it and copy the `AskForever` folder into:
   `World of Warcraft\_forever_\Interface\AddOns\`
3. It should look like: `...\AddOns\AskForever\AskForever.toc`

## 4. Install the companion

The companion is the app that connects the addon to the AI. Without it, AskForever can only build a prompt for you to copy.

1. Go to **[AskForever GitHub Releases](https://github.com/warcrafted-server/AskForever/releases)**.
2. Download the latest **`AskForever-Setup.exe`**.
3. Run it and follow the installer.
   - If Windows shows **"Windows protected your PC"** (SmartScreen), click **More info** → **Run anyway**. This happens with new apps from small authors.

![Companion installer](img/guide-setup.png) <!-- TODO screenshot -->

## 5. First-run wizard

When the installation finishes, the wizard opens:

1. **WoW folder**: `_forever_` is detected automatically. If not, click *Browse* and pick the `World of Warcraft\_forever_` folder.
2. **AI engine**: keep **Google Gemini (free)**.
3. **Key**: paste the key from step 2 and click **Test**. You should see ✅.
4. **Prepare the addon**: the wizard creates helper files the addon needs to receive answers (`AskForever_Slot…` folders). Don't delete them.
5. **Start with Windows**: keep it enabled so you never have to open the companion by hand.

The companion lives in the **system tray** (next to the clock).

![Companion wizard](img/guide-wizard.png) <!-- TODO screenshot -->

## 6. Restart WoW (first time only)

If the game was open, **close it completely and start it again**. A `/reload` is not enough: the game only detects new addons at startup.

At character select, click **AddOns** and make sure **AskForever** is enabled.

## 7. Your first question

1. Log in with your character.
2. Type `/af test` in chat. It should reply **"✅ Connection OK"**. If not, see [Troubleshooting](#9-troubleshooting).
3. Open AskForever with `/af` or your keybind (set it in *Options → Keybindings → AskForever*).
4. Type your question, e.g.: *how do I get to The Barrens?*
5. Within a few seconds you'll see the answer. Click **Take me there** to add map pins and an arrow.

No need to say your level, faction or location: AskForever already knows.

![First question](img/guide-first-question.png) <!-- TODO screenshot -->

## 8. Other AI engines (optional)

In the companion: right-click the tray icon → **Settings** → **AI engine**.

| Engine | Cost | What you need |
|---|---|---|
| **Google Gemini** (default) | Free | Key from [AI Studio](https://aistudio.google.com/) |
| **OpenAI-compatible API** (OpenCode, OpenRouter…) | Provider pricing | Base URL, key and model name |
| **Claude** | Pay per use | API key from [Claude Console](https://console.anthropic.com/) (a claude.ai Pro subscription does not work) |
| **Ollama** (local) | Free | [Ollama](https://ollama.com/) installed and a model downloaded; a GPU with 8 GB+ recommended |

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `/af` does nothing | AskForever isn't enabled or you didn't restart WoW. See step 6. |
| `/af test` says "Companion not detected" | Open the companion (tray icon). Make sure the game isn't in exclusive fullscreen. |
| The answer shows in a window over the game instead of the addon | The answer files ran out or failed. Do `/reload` or run *Prepare the addon* again in the companion. |
| "Usage limit reached" | You exceeded Google's free limit. Wait a minute (or until tomorrow for the daily limit). |
| "Invalid key" | Copy the key again from AI Studio and paste it in *Settings*. |
| No answers inside dungeons or in combat | Intended: the question is queued and sent when you leave combat or the instance. |
| The colored strip in the corner is distracting | It only shows for a moment while the question is being sent. |

If the problem persists, open a [GitHub issue](https://github.com/warcrafted-server/AskForever/issues) with your `/af test` output.

## 10. Uninstall

1. Companion: *Windows Settings → Apps → AskForever → Uninstall*. It offers to delete the `AskForever_Slot…` folders too.
2. Addon: uninstall it in CurseForge or delete `Interface\AddOns\AskForever`.
3. Optionally, delete your key in [AI Studio](https://aistudio.google.com/).

## 11. FAQ

**Is it free?** Yes, the addon and the companion are free. With Gemini, so is the AI.

**Can I get banned?** AskForever doesn't simulate input, read game memory or automate actions: it only displays information. Still, Blizzard has not stated a position on this kind of tool, so we can't guarantee anything. Use at your own risk.

**What data is sent?** Your question and character context (level, class, faction, zone, coordinates, quests). Nothing from your account or passwords.

**Does it work on Mac or Linux?** Windows only for now.
