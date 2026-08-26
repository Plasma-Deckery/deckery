# deckery-tray

**Repository:** [Plasma-Deckery/deckery](https://github.com/Plasma-Deckery/deckery) (bundled in the main repo, under `tray/`)

System tray applet that monitors and controls the full Deckery stack from a single icon in the KDE panel.

![Deckery tray menu](../assets/tray-cropped.png)

## What it does

- **Service status** — live display of the running state of makima and the HUD in the tray menu
- **Pause / Resume** — sends `pause` / `resume` over the makima IPC socket without restarting the service
- **Restart / Start / Stop** — controls makima and deckery-hud via systemd user units
- **Updates** — "Search for Updates" entry pulls all repos and re-runs the installer
- **Config folder** — opens `~/.config/deckery/` in the file manager for quick access
- **Steam Input** — shows whether Steam's Desktop Input is disabled (green) or still active (yellow); clicking the yellow indicator opens a terminal that writes the configset entry and optionally restarts Steam
- **Tooltip** — always shows "Deckery" on hover for quick identification

## Architecture

Built with GTK3 + AyatanaAppIndicator3. Runs inside the `deckery` distrobox container, launched via the `deckery-tray-launch` wrapper script.

**Service hierarchy:**

```
plasma-core.target  ← KDE-only, not active in Gamescope/Gaming Mode
    └── deckery-tray.service  ← owns the distrobox container, starts on login
            ├── makima.service       (BindsTo tray — cannot run without it)
            └── deckery-hud.service  (BindsTo tray — cannot run without it)
```

`deckery-tray.service` is bound to `plasma-core.target` (a KDE-specific systemd target that is not active in Gamescope/Gaming Mode). An `ExecCondition` guard additionally confirms that `plasma-plasmashell.service` is running before the tray starts — if the check fails, the service is skipped cleanly without triggering a restart loop. This means Deckery does not start in Gaming Mode and does not interfere with Gamescope.

`deckery-tray.service` runs `podman start deckery` before launching the tray, ensuring the container's main `conmon` process always lands in the tray's cgroup. This makes the tray the true owner of the container — stopping the tray stops everything cleanly.

**State tracking:**

| Source | Used for |
|---|---|
| `systemctl --user is-active` | Running state of makima and deckery-hud |
| `/tmp/makima-state.json` | Pause state of makima (field `paused`) |
| `/tmp/makima-control.sock` | Sending pause / resume commands |
| `configset_controller_neptune.vdf` | Steam Input configured state (polled every 2 s) |

Status updates run on a background thread to keep the GTK main loop responsive. A `Gio.FileMonitor` on `makima-state.json` triggers an immediate debounced refresh (120 ms window) whenever the file changes — pause state changes appear in the menu within milliseconds.

## Related

- [makima-deckery](makima-deckery/index.md) — produces the state JSON and IPC socket
- [deckery-hud](deckery-hud.md) — managed by the tray as a dependent service
