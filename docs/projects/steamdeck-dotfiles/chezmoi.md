# Chezmoi & Tracking

The dotfiles are managed with [chezmoi](https://www.chezmoi.io/), which tracks config files across the system and keeps them under version control.

## What chezmoi tracks

| Path | What it is |
|---|---|
| `dot_config/private_kwinrc` | KWin settings — focus policy, effects, window gaps, tiling |
| `dot_config/kwinoutputconfig.json` | Display config — scale (1.1), rotation, refresh rate, brightness curve |
| `dot_config/private_plasma-org.kde.plasma.desktop-appletsrc` | Panel layout — dock, taskbar, activity bar, desktop switcher |
| `dot_config/private_plasmashellrc` | Plasma shell settings — panel visibility, floating |
| `dot_config/private_kdeglobals` | Global KDE theme, colours, fonts |
| `dot_config/private_kglobalshortcutsrc` | Global keyboard shortcuts |
| `dot_config/private_kwinrulesrc` | Per-window rules (Firefox PiP always on top) |
| `dot_config/kcminputrc` | Pointer acceleration profile (flat) and Steam Controller scroll factor |
| `dot_config/private_powerdevilrc` | Power management — display timeout, auto-suspend, power button action |
| `dot_local/share/kwin/scripts/steam-keyboard-focus-fix/` | Custom KWin script — restores focus after Steam OSK appears |
| `dot_config/pipewire/filter-chain.conf.d/source-rnnoise.conf` | RNNoise voice filter |
| `dot_config/deckery/symlink_Steam Deck.toml` | Symlink to the makima base config |
| `dot_config/autostart/` | Autostart entries (Kando, OpenWhispr, Bitwarden) |
| `dot_config/gtk-3.0/`, `dot_config/gtk-4.0/` | GTK theme, font, cursor settings |
| `Brewfile` / `flatpaks.txt` | Package manifests |

## Run scripts (applied by chezmoi on change)

| Script | What it does |
|---|---|
| `run_onchange_30-install-maximized-window-gaps.sh` | Installs the maximized-window-gaps KWin script via `kpackagetool6` |
| `run_onchange_31-install-better-dynamic-workspaces.sh` | Installs the Kyanite KWin script |
| `run_onchange_32-install-steam-keyboard-focus-fix.sh` | Enables the steam-keyboard-focus-fix KWin script and reloads KWin |
| `run_onchange_40-install-udev-rules.sh` | Installs udev rules |

## What is not tracked

- Flatpak installs via Bazzite portal
- Decky Loader install steps
- Secrets and credentials
- Actions performed through system settings GUIs that do not write to tracked config files

## A note on applying these configs

This repo is a personal system backup, not a standalone installer. Running `chezmoi apply` from it would apply the entire personal setup — including shell config, editor settings, and other unrelated files — which is likely not what you want.

If you want to adopt parts of this setup, browse the repo directly and copy the relevant files manually. The [main documentation page](index.md) explains what each setting does and how to apply it independently.
