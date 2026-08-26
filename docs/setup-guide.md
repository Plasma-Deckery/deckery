# Setup Guide

## 1. Installation

**Requirements:**

- Steam Deck running [Bazzite](https://bazzite.gg) (or another Atomic Desktop with KDE Plasma + Wayland)
- [`distrobox`](https://distrobox.it/#installation) (pre-installed on Bazzite; install manually on other distributions)
- Internet connection

Paste this into a terminal — it clones the repo and runs the installer:

```bash
curl -sSL https://raw.githubusercontent.com/Plasma-Deckery/deckery/main/get.sh | bash
```

Or, if you prefer to inspect first:

```bash
git clone https://github.com/Plasma-Deckery/deckery.git ~/.local/share/deckery/deckery
bash ~/.local/share/deckery/deckery/install.sh
```

Re-running is safe — the script is idempotent. See [Installer Script](reference/installer-script.md) for details.

After setup, **Deckery** appears in your application launcher. Opening it starts the system tray icon — a small D-pad icon in the taskbar. If the tray icon is visible and shows all services as active, the installation is complete.

## 2. Configure Steam Input for coexistence

Steam has its own default button mapping for desktop mode. Deckery disables it entirely using Steam's own **Local Selection** mechanism: it writes a single entry into `configset_controller_neptune.vdf` that points Steam's Desktop controller profile to its built-in `empty.vdf`, which contains no bindings at all. No sudo is required, and Steam updates work normally.

### The Steam Input tray item

The Deckery tray polls the configset file every 2 seconds and shows the current state in the menu under **Steam Input**:

| Indicator | State | Meaning |
|---|---|---|
| Green | **Steam Input: disabled** | The configset entry is in place — no action needed |
| Yellow | **Steam Input: still active** | The entry is missing — click to disable |

Clicking the yellow item opens a Konsole terminal that writes the configset entry and optionally restarts Steam to apply it immediately.

### During install

The installer asks whether you want to disable Steam Input now. If you choose yes, it writes the configset entry immediately. If you skip it (or run in non-interactive mode), you can do it at any time by clicking the yellow tray item.

## Updates

The easiest way to update is the **Check for Updates** entry in the Deckery tray menu. It checks for a new release and opens a terminal that runs the full update automatically.

To update manually:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Plasma-Deckery/deckery/main/get.sh)
```

This fetches the latest release tag and re-runs the installer — the same steps the tray menu triggers.

!!! warning "Do not use `git pull && install.sh` to update"
    That would stay on the `main` branch rather than checking out the latest release tag. Always use `get.sh` for updates.

## Uninstall

To remove all Deckery services, binaries, and the distrobox container:

```bash
bash ~/.local/share/deckery/deckery/uninstall.sh
```

This will ask for confirmation before doing anything. Pass `--yes` to skip:

```bash
bash ~/.local/share/deckery/deckery/uninstall.sh --yes
```

**What gets removed:**

- All Deckery systemd user services (stopped, disabled, and deleted)
- Installed binaries and symlinks in `~/.local/bin/`
- The `deckery` distrobox container
- The app icon and `.desktop` launcher
- The `Steam Deck.toml` config symlink in `~/.config/deckery/`

**What is kept:**

- The cloned repos in `~/.local/share/deckery/` (your configs live there)
- App-specific config files in `~/.config/deckery/`

To also remove the repos and all custom configs, delete `~/.local/share/deckery/` manually after uninstalling.
