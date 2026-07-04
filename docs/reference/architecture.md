# Architecture

## Service hierarchy

```
deckery-tray.service              ← starts on login, manages the stack
    ├── makima.service             (PartOf tray — stops/restarts with it)
    │       └── makima-resume-watcher.service  (BindsTo makima — starts/stops with it)
    └── deckery-hud.service        (PartOf tray — stops/restarts with it)
```

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
