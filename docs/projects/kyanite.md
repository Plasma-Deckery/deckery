# Kyanite

**Fork:** [Plasma-Deckery/kyanite](https://github.com/Plasma-Deckery/kyanite)
**Upstream:** [MurderFromMars/Kyanite](https://github.com/MurderFromMars/Kyanite)

KWin script for dynamic workspace management. Kyanite ensures there is always at least one empty workspace available — you never have to create or delete workspaces manually. Windows are placed automatically.

## Why it's in Deckery

On a small screen, vertical workspace switching (rotating around the short edge) works better than horizontal. Kyanite's dynamic management means workspaces grow and shrink automatically as you open and close apps — one less thing to think about.

## What was changed

The upstream Kyanite supports multiple grid layouts. The Deckery fork patches in a **single-column vertical grid** layout, so workspace switching always moves up/down rather than left/right.

Contributed back upstream as [MurderFromMars/Kyanite#3](https://github.com/MurderFromMars/Kyanite/pull/3).
