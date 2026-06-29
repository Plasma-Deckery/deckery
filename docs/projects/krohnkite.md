# Kröhnkite

**Upstream:** [esjeon/krohnkite](https://github.com/esjeon/krohnkite)
**Deckery fork:** not yet — used unmodified

KWin script for dynamic window tiling. Kröhnkite automatically arranges windows in tiling layouts (spiral, columns, monocle, etc.) and lets you switch between them on the fly.

## Why it's in Deckery

Maximising screen use on a small display without touching the mouse or trackpad is the goal. Kröhnkite handles layout management entirely via keyboard shortcuts — which makima-deckery can map to controller buttons.

## Using Kröhnkite with makima

With the right config, controller shortcuts can drive the full Kröhnkite feature set:

- Toggle fullscreen for the focused window
- Cycle through tiling layouts
- Move focus between windows (up/down/left/right)
- Float/unfloat a window

Map these to makima bindings in your `Steam Deck.toml`. Example:

```toml
# Toggle tiling layout (example binding)
R4 = "key Super+Return"
```

## Planned

A Deckery-specific Kröhnkite config with sensible Steam Deck defaults is planned but not yet documented.
