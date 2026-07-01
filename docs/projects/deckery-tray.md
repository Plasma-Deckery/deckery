# deckery-tray

**Repository:** [Plasma-Deckery/deckery](https://github.com/Plasma-Deckery/deckery) (bundled in the main repo, under `tray/`)

System tray applet that monitors and controls the full Deckery stack from a single icon in the KDE panel.

![Deckery tray menu](../assets/tray-cropped.png)

## What it does

- **Service status** — live display of the running state of makima and the HUD in the tray menu
- **Pause / Resume** — sends `pause` / `resume` over the makima IPC socket without restarting the service
- **Restart / Start / Stop** — controls makima and deckery-hud via systemd user units
- **Updates** — "Search for Updates" entry pulls all repos and re-runs the installer
- **Config folder** — opens `~/.config/makima/` in the file manager for quick access
- **Tooltip** — always shows "Deckery" on hover for quick identification

## Architecture

Built with GTK3 + AyatanaAppIndicator3. Runs inside the `deckery` distrobox container, launched via the `deckery-tray-launch` wrapper script.

**Service hierarchy:**

```
deckery-tray.service  ← owns the distrobox container, starts on login
    ├── makima.service       (PartOf tray — stops/restarts with it)
    └── deckery-hud.service  (PartOf tray — stops/restarts with it)
```

`deckery-tray.service` runs `podman start deckery` before launching the tray, ensuring the container's main `conmon` process always lands in the tray's cgroup. This makes the tray the true owner of the container — stopping the tray stops everything cleanly.

**State tracking:**

| Source | Used for |
|---|---|
| `systemctl --user is-active` | Running state of makima and deckery-hud |
| `/tmp/makima-state.json` | Pause state of makima (field `paused`) |
| `/tmp/makima-control.sock` | Sending pause / resume commands |

Status updates run on a background thread to keep the GTK main loop responsive. A `Gio.FileMonitor` on `makima-state.json` triggers an immediate debounced refresh (120 ms window) whenever the file changes — pause state changes appear in the menu within milliseconds.

## Related

- [makima-deckery](makima-deckery/index.md) — produces the state JSON and IPC socket
- [deckery-hud](deckery-hud.md) — managed by the tray as a dependent service
