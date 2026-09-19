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
               └─ $XDG_RUNTIME_DIR/makima-control.sock
                                          ◄── deckery-tray (pause, Gaming Mode,
                                              switching configs and groups)
```

There is no request/response anywhere in this picture, and that is deliberate. The tray sends a command and then reads the result out of `state.json` like any other observer. One writer, one truth — which is what keeps a reload and a restart from ever disagreeing about which configs are active, and why an operation like "switch a whole exclusive group off" is resolved inside makima rather than assembled from several tray commands.

## Config flow

Configs are not part of the runtime picture above; they are resolved before an event is ever translated.

```
~/.local/share/deckery/deckery/configs   (shipped — replaced on every update)
/usr/share/deckery/configs               (shipped, RPM install)
~/.config/deckery                        (yours — never written to but README.md)
       │
       └─► ConfigRegistry ──► apply_preferences (preferences.toml)
                  │
                  └─► resolve(base, focused window, layout) ──► Arc<Config> ──► EventReader
```

Every `.toml` in either directory is picked up by being there — there is no include list and nothing is registered anywhere. A file's role follows from its content: a `[device]` section makes it a base config, `match_window_class` an app override, `layout = N` a layout module, anything else a plain module merged into every base config.

Entries are keyed by file base name and the shipped root is read first, so a file of yours replaces the shipped one of the same name — **if it parses**. When it does not, the shipped config stays in effect and the entry carries a warning naming the file that was skipped.

`resolve()` is memoised per `(base config, window class, layout)`, because it runs on the input path and the merged config holds several maps that would otherwise be deep-copied on every key press. Any change that could affect the answer — a file written, a config toggled, the compositor detected — clears the memo.

See [Configuration](../configuration.md) for the layering rules and [Config Registry architecture](https://github.com/Plasma-Deckery/makima-deckery/blob/main/docs/config-registry.md) for the implementation.

## Where the code lives

**makima-deckery** (Rust), the parts worth knowing before reading it:

| Area | Files |
|---|---|
| Config | `config.rs` (parse + merge), `config_registry.rs` (discovery, layering, activation), `preferences.rs`, `resolver.rs` |
| Input | `event_reader.rs` (translation, emission, pointer emulation, IPC), `udev_monitor.rs` (device discovery), `virtual_devices.rs` |
| Trackpads | `trackpad.rs`, `trackpad_router.rs`, `mt_trackpad.rs`, `gesture_pad.rs`, `scroll_pad.rs`, `trackball.rs` |
| Compositor | `compositor/` — one adapter per desktop (`kde.rs`, `hyprland.rs`, `fallback.rs`) |
| State out | `state_export.rs` (build the snapshot), `state_writer.rs` (write it, skipping unchanged content) |

**deckery** (Python/GTK3): `tray/deckery-tray.py` is the applet and the only reader of systemd state; `tray/config_menu.py` owns the Controller Bindings submenu; `tray/setup/` is the onboarding wizard, one module per page.
