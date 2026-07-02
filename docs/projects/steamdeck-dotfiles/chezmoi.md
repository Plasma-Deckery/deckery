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

## Applying on a fresh system

1. Install chezmoi
2. Initialise from this repo: `chezmoi init https://github.com/Plasma-Deckery/steamdeck-dotfiles`
3. Apply: `chezmoi apply`
4. Install Homebrew packages: `brew bundle`
5. Restore Flatpaks: `xargs flatpak install < flatpaks.txt`
6. Perform non-tracked steps manually (Decky Loader, Bazzite portal actions)

!!! note "Documentation still in progress"
    The full setup guide for non-tracked steps is not yet written. If you know chezmoi, the above is enough to get started.
