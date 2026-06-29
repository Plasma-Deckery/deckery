# Setup Guide

## Requirements

- Steam Deck running [Bazzite](https://bazzite.gg) (or another Atomic Desktop with KDE Plasma + Wayland)
- `distrobox` (pre-installed on Bazzite)
- Internet connection for the initial install

## Installation

Clone the deckery repo and run the installer:

```bash
git clone https://github.com/Plasma-Deckery/deckery.git ~/Programming/deckery
bash ~/Programming/deckery/install.sh
```

The installer:
1. Clones **makima-deckery** and **deckery-hud** next to the deckery repo
2. Builds makima inside the `deckery` distrobox container
3. Installs all three systemd user services (makima, deckery-hud, deckery-tray)
4. Symlinks the default config to `~/.config/makima/`

Re-running is safe — the script is idempotent.

## Configure Steam Input for coexistence

Steam Input must be minimally configured so it doesn't conflict with makima-deckery on the inputs Deckery owns. A ready-to-use desktop config is included in [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles) at `dot_local/share/Steam/controller_base/executable_desktop_neptune.vdf` — it disables almost everything in Steam Input except the trackpads and the Steam button, and moves the on-screen keyboard to Steam+X.

Copy it into place:

```bash
cp executable_desktop_neptune.vdf \
  ~/.local/share/Steam/controller_base/desktop_neptune.vdf
```

Then **lock the file** so Steam can't overwrite it on updates or restarts:

```bash
sudo chattr +i ~/.local/share/Steam/controller_base/desktop_neptune.vdf
```

**Why the lock?** Steam silently resets `desktop_neptune.vdf` to its defaults whenever it updates or rewrites its controller config. The `chattr +i` immutable flag prevents any process (including Steam running as your user) from modifying or replacing the file.

> ⚠️ **Warning:** The `chattr +i` lock blocks Steam's updater from doing an atomic rename on this file, which causes the entire Steam client update to fail and corrupt the installation. A better solution is being tracked in [deckery#11](https://github.com/Plasma-Deckery/deckery/issues/11) — replacing the lock with a makima file watcher that restores the config after updates without blocking them.

## Verify the installation

After setup, check that all services are running:

```bash
systemctl --user status makima.service deckery-hud.service deckery-tray.service
```

Hold **L1** on your Steam Deck — the HUD overlay should appear showing the current button map.

## Your config

The base config lives at `~/Programming/deckery/configs/Steam Deck.toml` and is symlinked to `~/.config/makima/Steam Deck.toml`. Edits there are tracked by git.

App-specific configs (`Steam Deck::*.toml`) live directly in `~/.config/makima/` and are not version-controlled — they are yours to customize freely.
