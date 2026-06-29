# steamdeck-dotfiles

**Repository:** [Plasma-Deckery/steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles)

An opinionated KDE Plasma desktop setup tuned for the Steam Deck's screen size and input methods. Managed via [chezmoi](https://www.chezmoi.io/).

## What's included

- KDE panel layout optimised for the 800p screen
- KWin configuration for use with [Kyanite](kyanite.md) and [Kröhnkite](krohnkite.md)
- Steam Input desktop config (`desktop_neptune.vdf`) — disables Steam Input for everything except trackpads and the Steam button, moves the on-screen keyboard to Steam+X
- RNNoise pipeline configuration for noise suppression during voice input outdoors
- Various system settings and scripts

## Steam Input config

The included `desktop_neptune.vdf` is the recommended starting point for coexistence with makima-deckery. See [Setup Guide](../setup-guide.md) for how to install and lock it.

> ⚠️ Documentation for this repo is still incomplete. More detail will be added as the setup stabilises.
