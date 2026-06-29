# maximized-window-gaps

**Fork:** [Plasma-Deckery/maximized-window-gaps](https://github.com/Plasma-Deckery/maximized-window-gaps)
**Upstream:** [KSmanis/kwin-scripts](https://github.com/KSmanis/kwin-scripts) (maximized-window-gaps)

KWin script that adds configurable gaps around maximized windows. Without gaps, maximized windows feel cramped on a small screen — a few pixels of breathing room around the edges makes the desktop noticeably more comfortable.

## Why it's in Deckery

KDE's default tiling and maximization don't leave any margin around windows. On the Steam Deck's 800p display, this makes the screen feel cluttered. The gaps script adds a consistent inset that improves readability and visual comfort.

## What was changed

The upstream script had incorrect behaviour on the Steam Deck's screen geometry (1280×800). The Deckery fork corrects the gap calculations so they apply correctly on this resolution.
