# Chezmoi & Tracking

The dotfiles are managed with [chezmoi](https://www.chezmoi.io/), which tracks config files across the system and keeps them under version control.

## What chezmoi tracks

| Path | What it is |
|---|---|
| `dot_config/private_kwinrc` | KWin settings — tiling, focus policy, effects |
| `dot_config/private_plasma-org.kde.plasma.desktop-appletsrc` | Panel layout — dock, taskbar, activity bar |
| `dot_config/private_kglobalshortcutsrc` | Global keyboard shortcuts |
| `dot_config/private_kwinrulesrc` | Per-window rules |
| `dot_config/pipewire/filter-chain.conf.d/source-rnnoise.conf` | RNNoise voice filter |
| `dot_config/makima/symlink_Steam Deck.toml` | Symlink to the makima base config |
| `dot_local/share/Steam/controller_base/executable_desktop_neptune.vdf` | Steam Input desktop config |
| `dot_config/autostart/` | Autostart entries (Kando, OpenWhispr) |
| `Brewfile` / `flatpaks.txt` | Package manifests |

## What is not tracked

- Flatpak installs via Bazzite portal
- Decky Loader install steps
- Secrets and credentials
- Actions performed through system settings GUIs that do not write to tracked config files

## A note on applying these configs

This repo is a personal system backup, not a standalone installer. Running `chezmoi apply` from it would apply the entire personal setup — including shell config, editor settings, and other unrelated files — which is likely not what you want.

If you want to adopt parts of this setup, browse the repo directly and copy the relevant files manually. The table above shows what each file controls.
