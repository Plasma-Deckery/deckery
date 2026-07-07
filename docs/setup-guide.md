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

Re-running is safe — the script is idempotent. See [Installer Script](reference/installer-script.md) for details.

After setup, **Deckery** appears in your application launcher. Opening it starts the system tray icon — a small D-pad icon in the taskbar. If the tray icon is visible and shows all services as active, the installation is complete.

## 2. Configure Steam Input for coexistence

Steam has its own default button mapping for desktop mode. Deckery needs to take control of most inputs — but this mapping cannot be fully disabled from within Steam. Instead, Deckery overwrites Steam's config file with a minimal layout, so the two don't conflict.

A few features from the original Steam layout are kept and adapted:

- **Trackpad handling** — the trackpads continue to work as before
- **On-screen keyboard** — moved to **Steam + X**

The installer places the config in two locations:

- `~/.config/makima/desktop_neptune.vdf` — the canonical copy the tray reads from
- `~/.local/share/Steam/controller_base/desktop_neptune.vdf` — Steam's active config

### The Steam config tray item

The Deckery tray monitors the config file continuously and shows its state in the menu under **Steam config**:

| Indicator | State | Meaning |
|---|---|---|
| 🟢 | **locked** | Config is in place and protected — no action needed |
| 🟡 | **unlocked** | Config is correct but unprotected — Steam will overwrite it on next start |
| 🔴 | **Fix and Lock** | Steam has overwritten the config — click to restore and lock |
| 🟡 | **source missing** | The canonical copy in `~/.config/makima/` is gone |

### After a fresh install

After running the installer the file is in place but not locked. The tray shows **unlocked** (yellow).

Click the **Steam config: unlocked** item — a terminal opens, enters `sudo chattr +i`, and locks the file. The tray turns green.

### When Steam overwrites the config

Steam silently restores its defaults every time it starts. If it does, the tray turns **red**.

Click the red **Steam config: Fix and Lock** item — a terminal opens, copies the canonical config back, locks it, and the tray returns to green.

### When Steam needs to update

The `chattr +i` lock prevents Steam's update mechanism from doing its atomic file rename, which aborts the entire client update. Before updating Steam:

1. Click **Unlock for Steam update** in the tray → terminal unlocks the file, tray turns yellow
2. Open Steam → let it update (it will overwrite the config in the process)
3. Click the red **Steam config: Fix and Lock** item → terminal restores and re-locks the file, tray turns green

!!! info "All terminal steps require your sudo password"
    `chattr +i/-i` requires root privileges. Each terminal walks you through the operation and shows a ✓ or ✗ result before closing.

Full technical background and plans for future automation in [deckery#11](https://github.com/Plasma-Deckery/deckery/issues/11).

## Updates

To update all components:

```bash
cd ~/.local/share/deckery/deckery && git pull && bash install.sh
```

Or use the **Search for Updates** entry in the Deckery tray menu.

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
- The `Steam Deck.toml` config symlink in `~/.config/makima/`

**What is kept:**

- The cloned repos in `~/.local/share/deckery/` (your configs live there)
- App-specific config files in `~/.config/makima/`
- `desktop_neptune.vdf` (Steam Input config)

To also remove the repos and all custom configs, delete `~/.local/share/deckery/` manually after uninstalling.
