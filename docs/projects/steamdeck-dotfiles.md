# Steam Deck Dotfiles

**Repository:** [Plasma-Deckery/steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles)

An opinionated KDE Plasma desktop setup tuned for the Steam Deck's screen size and input methods. Managed via [chezmoi](https://www.chezmoi.io/).

The goal is a desktop that works well with a controller and no keyboard — clean, fast to navigate, and organised so you always know where things are.

## Layout

The panel layout is built around the Steam Deck's portrait-friendly screen:

- **Dock** on the left — app launcher and pinned applications
- **Desktop switcher** on the right — vertical spaces, always visible
- **Taskbar** at the top — system tray, clock, status icons
- **Activity bar** at the bottom — switch between named activity contexts

![Desktop layout with activities](../assets/dotfiles-activities.png)

## Activities and workspaces

KDE Activities act as separate desktops with their own sets of virtual spaces. Each activity has a dedicated purpose — Coding, Gaming, Music, 2nd-Brain, Deck, Random — so apps for different contexts never mix.

Within each activity, each virtual desktop holds at most one or two applications. Apps open in tiling mode and automatically fill the available space, so there is never a need to move or resize windows manually.

<video src="../assets/tiling.mp4" controls autoplay loop muted></video>

## Dynamic workspace management

A KWin script ([Kyanite](kyanite.md)) ensures there is always exactly one free desktop available at the end of the list. When you close the last app on a space, that space is cleaned up automatically. When all spaces are occupied, a new one is created. This means workspace management is fully automatic — you never have to create or delete desktops manually.

<video src="../assets/desktopswitch.mp4" controls autoplay loop muted></video>

## Focus follows mouse

The pointer focus policy is set so that moving the cursor to a window focuses it immediately, without clicking. On a small screen with a trackpad, this removes a significant source of friction.

## Voice input

A [RNNoise](https://github.com/xiph/rnnoise) PipeWire filter-chain is configured for noise suppression during voice input. This is particularly useful outdoors. Works together with [OpenWhispr](openwhispr.md) for hotkey-activated speech-to-text.

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

!!! note "Documentation still in progress"
    The full setup guide — how to apply these dotfiles on a fresh system — is not yet written. If you know chezmoi, initialising from the repo is straightforward.
