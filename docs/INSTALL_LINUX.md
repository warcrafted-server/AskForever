# AskForever installation guide for Linux (EN)

**[Versión en español](INSTALACION_LINUX.md)**

This guide covers installing and using AskForever on Linux. The first setup takes about **10 minutes**.

AskForever has two parts:

- The **addon**: the AskForever window inside World of Warcraft.
- **AskForever App**: a Linux app that connects the addon to the AI and shows answers over the game.

If you use Windows, read the [Windows installation guide](https://github.com/warcrafted-server/AskForever/blob/main/docs/INSTALL_GUIDE.md).

## Before you start

You need:

- **x86_64 Linux**. 0.5.0-beta.1 is the first Linux version and has only been tested on **Arch Linux and derivatives, with KDE Plasma on Wayland** and the game in Lutris. It is not tested on other desktops or distributions.
- Your **desktop portal** and a **Secret Service keyring** (KWallet or GNOME Keyring), plus the packages from step 1.
- World of Warcraft: **WoW Forever** installed and running with Wine or Proton (Lutris or Steam), in **borderless windowed** fullscreen mode.
- A **Google account**, free, to create the Gemini key.

## 1. Install the required packages

On Arch Linux and derivatives, install the packages needed for screen capture and the overlay:

```
sudo pacman -S --needed gstreamer gst-plugins-base gst-plugins-good gst-plugin-pipewire xdg-desktop-portal libx11 libxext
```

You also need your desktop's portal (on KDE, the `xdg-desktop-portal-kde` package) and a Secret Service keyring, such as KWallet or GNOME Keyring. AskForever App stores the AI key in that keyring.

## 2. Download and install AskForever

The Linux package installs the addon and AskForever App at once.

1. On the [latest release page](https://github.com/warcrafted-server/AskForever/releases/latest), download **`askforever-<version>-linux-x86_64.tar.gz`** and its **`.sha256`** file.
2. Check the download in the folder that contains both files:

   ```
   sha256sum -c askforever-<version>-linux-x86_64.tar.gz.sha256
   ```

3. Extract the package:

   ```
   tar -xzf askforever-<version>-linux-x86_64.tar.gz
   ```

4. Enter the `askforever-<version>` folder and run the installer. **No root is needed**:

   ```
   ./install.sh --desktop
   ```

   `install.sh` options:

   - `--wow-dir PATH`: the game's `_forever_` folder (or the `World of Warcraft` folder).
   - `--desktop`: adds an **AskForever App** shortcut to the applications menu. It is the only thing created outside the game folder.
   - `--help`: shows the help.

   Without `--wow-dir`, the installer looks for the game in the usual Lutris, Wine, Steam and Bottles prefixes. If it finds several or none, it asks for the folder.

5. When it finishes, open **AskForever App** from the applications menu.

The installer installs the app in `<_forever_>/AskForever/` and the addon in `<_forever_>/Interface/AddOns/AskForever`. In this guide, `<_forever_>` is the `_forever_` folder of your game installation. If the addon you already have installed is newer, it is kept. The addon can also be installed and updated from CurseForge.

If you prefer not to use the shortcut, open the app with:

```
<_forever_>/AskForever/AskForeverApp app
```

## 3. First launch: configure AI and screen sharing

1. On first launch, the **Configure AI** dialog opens for Google Gemini. Follow the [Gemini key guide](https://github.com/warcrafted-server/AskForever/blob/main/docs/GEMINI_KEY.md) to get a free key, enter it in the dialog and click **Test and save**. The app tests the key before saving it in the **desktop keyring** (`AskForever` service). The key is never saved in a file.
2. With WoW open, the desktop asks to **share your screen**: choose the monitor where the game is. The choice is remembered in `AskForever/data/portal-token`. To choose another monitor, delete that file and reopen the app.
3. AskForever App only captures the screen while the game is open.

## 4. Play

1. Keep **AskForever App running** while you play; the addon needs it to answer questions.
2. Start WoW Forever and log in.
3. In the game, type `/af` (or `/askforever`) in the game chat and press Enter, or click the **AskForever** button on the minimap. The AskForever chat window opens.
4. Type your question in that window and press Enter. For example: *How do I get to The Barrens?*
5. The answer appears in the conversation of the addon window. Scroll the conversation with the mouse wheel over it or use its arrow buttons, move the window and resize it from its bottom-right corner. The answer panel does not intercept clicks: they pass through it.

### AskForever App window and system tray

Closing the app window keeps it running in the system tray. Click the tray icon to reopen it; the icon menu has **Open** and **Quit**.

## Updates

- **AskForever App** only notifies you of a new version with its link; it does not download or run anything. To update, close the app, extract the new package and run `./install.sh` again. Your key and data are kept.
- **Addon, game data and guide cards:** update the **AskForever** addon in CurseForge, or install the new Linux package as explained above.

## Uninstall

With the app closed, run:

```
<_forever_>/AskForever/uninstall.sh
```

Add `--yes` to skip confirmation. This removes the key, the data, the logs, the addon, the app folder and the shortcut.

## Known limitations

- On GNOME, the tray icon needs an AppIndicator extension. It is not tested.
- With Wine or Proton on native Wayland, the panel does not hide when you switch to another window.
- Not tested: GNOME or other desktops and distributions, WoW under XWayland inside the game, X11 sessions, or several monitors with the game outside the left monitor.

## Common problems

| Problem | What to do |
|---|---|
| The screen-sharing dialog does not appear on KDE after a Qt update without logging out | Run `systemctl --user restart plasma-xdg-desktop-portal-kde.service xdg-desktop-portal.service`, or restart the computer, and reopen the app. |
| The screen-sharing dialog is not visible | Look for it with Alt+Tab or on the other monitor. It expires after two minutes and appears again. |
| The tray icon does not appear (GNOME) | Install an AppIndicator extension. It is not tested. |

### Logs

If something fails, check:

- `<_forever_>/AskForever/logs/app.log`: the app log.
- `<_forever_>/AskForever/companion.log`: the screen-capture log. It records its start, the first frame and GStreamer errors.

## Security and transparency

- **Screen:** the desktop portal shares the chosen monitor with a local `gst-launch-1.0` process, which crops the top-left 512 × 32 pixels. The app only receives that crop, does not save images and does not capture while the game is closed. The permission granted to the portal covers the whole monitor.
- **Game:** it detects WoW by reading the `/proc` process list (`Wow.exe` command line, environment and mapped files, only to find its folder). It does not read game memory, inject anything or simulate keyboard or mouse input.
- **Files:** `<_forever_>/AskForever/` holds the program, `data/`, `logs/` and the `companion.log`, `data/portal-token` and `data/portal-geometry.json` files. The addon's `data/` folder is read-only. The key is in the keyring and, if you use `--desktop`, `~/.local/share/applications/askforever.desktop` is added.
- **Network:** the same connections as on Windows (the chosen AI provider, warcraft.wiki.gg and GitHub). On Linux, it only reads the release list from GitHub and downloads the game database.

The [security and transparency report](https://github.com/warcrafted-server/AskForever/blob/main/docs/SECURITY_TRANSPARENCY.md) explains what AskForever App does and never does.

## Build from source (optional)

To build the package yourself, from the repository root:

```
python3 -m venv build/venv-linux && build/venv-linux/bin/pip install -e companion pyinstaller && bash scripts/build-linux.sh
```

The package is generated in `release/`. You need **Python 3.12 or later with tkinter**; on Arch Linux, the `tk` package.

The official Linux package is built in GitHub Actions from 0.5.0-beta.1, with SHA-256 and a provenance check that can be verified with `gh attestation verify`. There is no published VirusTotal analysis for Linux.
