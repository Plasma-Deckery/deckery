# Setup Guide

## 1. Installation

**Requirements:**

- Steam Deck running [Bazzite](https://bazzite.gg) (or another Atomic Desktop with KDE Plasma + Wayland)
- `distrobox` (pre-installed on Bazzite)
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

Re-running is safe — the script is idempotent. See [Installer Script](../reference/installer-script.md) for details.

After setup, **Deckery** appears in your application launcher. Opening it starts the system tray icon — a small D-pad icon in the taskbar. If the tray icon is visible and shows all services as active, the installation is complete.

## 2. Configure Steam Input for coexistence

Steam has its own default button mapping for desktop mode. Deckery needs to take control of most inputs — but this mapping cannot be fully disabled from within Steam. Instead, Deckery overwrites Steam's config file with a minimal layout, so the two don't conflict.

A few features from the original Steam layout are kept and adapted:

- **Trackpad handling** — the trackpads continue to work as before
- **On-screen keyboard** — moved to **Steam + X**

The Deckery config file is located at:

```
~/.local/share/deckery/deckery/docs/desktop_neptune.vdf
```

The installer copies this automatically on every run. To manually copy or restore it:

!!! info "Manually apply the config"
    ```bash
    cp ~/.local/share/deckery/deckery/docs/desktop_neptune.vdf \
       ~/.local/share/Steam/controller_base/desktop_neptune.vdf
    ```

!!! warning "Steam resets this config on every restart"
    Steam silently overwrites `desktop_neptune.vdf` with its defaults every time it restarts or updates. To prevent this, lock the file after placing it:

    ```bash
    sudo chattr +i ~/.local/share/Steam/controller_base/desktop_neptune.vdf
    ```

This approach has an inconvenient drawback.

!!! warning "Steam updates fail while the file is locked"
    The `chattr +i` immutable flag prevents Steam's update mechanism from doing its atomic rename on the config file, which **aborts the entire Steam client update**.

    Before installing a Steam update, unlock the file first — then restore and re-lock afterward:

    ```bash
    # Before the Steam update — unlock
    sudo chattr -i ~/.local/share/Steam/controller_base/desktop_neptune.vdf

    # After the Steam update — restore and re-lock
    cp ~/.local/share/deckery/deckery/docs/desktop_neptune.vdf \
       ~/.local/share/Steam/controller_base/desktop_neptune.vdf
    sudo chattr +i ~/.local/share/Steam/controller_base/desktop_neptune.vdf
    ```

A permanent solution using a file watcher that automatically restores the config after Steam updates is planned in [deckery#11](https://github.com/Plasma-Deckery/deckery/issues/11).

## Updates

To update all components:

```bash
cd ~/.local/share/deckery/deckery && git pull && bash install.sh
```

Or use the **Search for Updates** entry in the Deckery tray menu.
