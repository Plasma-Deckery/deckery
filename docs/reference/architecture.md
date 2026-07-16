# Architecture

## Service hierarchy

```
plasma-core.target                ← KDE-only, not active in Gamescope/Gaming Mode
    └── deckery-tray.service      ← starts on login, manages the stack
            ├── makima.service         (BindsTo tray — cannot run without it)
            └── deckery-hud.service    (BindsTo tray — cannot run without it)
```

`deckery-tray.service` uses `BindsTo=plasma-core.target` and an `ExecCondition` guard that confirms `plasma-plasmashell.service` is active before starting. In Gaming Mode (Gamescope), `plasma-core.target` is not active and the guard check fails — Deckery does not start and does not interfere with Gamescope.

## Data flow

```
/dev/input/event* (evdev)
       │
       └─ makima-deckery ───────────────────► virtual keyboard / mouse
               │                             └─► virtual trackpad MT devices
               │                                          │
               │                                          └─► libinput / gesture tools
               │
               ├─ /tmp/makima-state.json  ──► deckery-hud  (live overlay)
               │                         └──► deckery-tray (status display)
               └─ /tmp/makima-control.sock ◄── deckery-tray (pause / resume)
```
