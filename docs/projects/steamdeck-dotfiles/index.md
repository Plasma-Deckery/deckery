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

![Desktop layout with activities](../../assets/dotfiles-activities.png)

## Activities and workspaces

KDE Activities act as separate desktops with their own sets of virtual spaces. Each activity has a dedicated purpose — Coding, Gaming, Music, 2nd-Brain, Deck, Random — so apps for different contexts never mix.

Within each activity, each virtual desktop holds at most one or two applications. Apps open in tiling mode and automatically fill the available space, so there is never a need to move or resize windows manually.

<video src="../../assets/tiling.mp4" controls autoplay loop muted></video>

## Window tiling

[Kröhnkite](../krohnkite.md) provides dynamic window tiling — windows automatically arrange to fill the available space without manual resizing. [maximized-window-gaps](../maximized-window-gaps.md) adds configurable gaps around tiled windows so the layout breathes a little on the small screen.

## Dynamic workspace management

A KWin script ([Kyanite](../kyanite.md)) ensures there is always exactly one free desktop available at the end of the list. When you close the last app on a space, that space is cleaned up automatically. When all spaces are occupied, a new one is created. Workspace management is fully automatic — you never have to create or delete desktops manually.

<video src="../../assets/desktopswitch.mp4" controls autoplay loop muted></video>

## Focus follows mouse

The pointer focus policy is set so that moving the cursor to a window focuses it immediately, without clicking. On a small screen with a trackpad, this removes a significant source of friction.

KWin's focus stealing prevention is set to Medium — this stops the Steam on-screen keyboard from grabbing focus away from the app you're typing into, so input lands where you intended.

## Voice input

A [RNNoise](https://github.com/xiph/rnnoise) PipeWire filter-chain is configured for noise suppression during voice input. This is particularly useful outdoors. Works together with [OpenWhispr](../openwhispr.md) for hotkey-activated speech-to-text.
