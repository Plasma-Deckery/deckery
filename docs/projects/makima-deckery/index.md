# Makima Deckery

**Repository:** [Plasma-Deckery/makima-deckery](https://github.com/Plasma-Deckery/makima-deckery)
**Fork of:** [cyber-sushi/makima](https://github.com/cyber-sushi/makima)

The heart of Deckery — the input remapper. Reads raw evdev events directly from the kernel, applies a TOML config, and emits keyboard/mouse events via uinput. Supports per-app layouts, modifier keys, and trackpad gesture devices.

## What it does

- **Steam independence** — reads `/dev/input/event*` directly, no Steam Input in the loop
- **Context-aware layouts** — per-app configs loaded automatically based on the focused window, with config inheritance so overrides only declare what differs
- **Modifier keys** — hold a button to activate a second layer of bindings
- **Trackpad MT devices** — exposes the Steam Deck trackpads as standard uinput multi-touch devices for libinput and gesture tools
- **HUD state export** — writes a fully-resolved state snapshot to `/tmp/makima-state.json` on every input event for deckery-hud to consume
- **IPC control socket** — pause, resume, and configure the service at runtime via `/tmp/makima-control.sock`

## What's different from upstream

| Change | Description |
|---|---|
| Bug fixes | D-Pad remapping, x11rb Wayland crash, evdev reconnect on device error |
| Event-driven window focus | KWin D-Bus script replaces `kdotool` subprocess spawning — no polling, no latency |
| Config inheritance | App overrides only declare what differs; base config is merged at runtime |
| Binding attributes | `label`, `no_pause` per binding — see [Bindings](bindings.md) |
| State export | `/tmp/makima-state.json` — see [State JSON](../../reference/state-json.md) |
| Trackpad MT translation *(on `main`, not yet released)* | Both pads emulated as standard system touchpad devices — see [Trackpad](trackpad.md) |
| Pause / Resume IPC | Runtime control via Unix socket — see [IPC](../../reference/ipc.md) |
| Steam Deck keycodes | `BTN_GRIPL/R/L2/R2` for back paddles via patched `evdev` crate |
| Unit test suite | 69 tests covering resolver, state export, analog helpers, and config parsing |

## Bug fixes submitted upstream

| Fix | PR | Why |
|---|---|---|
| `BTN_DPAD_*` keys silently ignored in config | [#57](https://github.com/cyber-sushi/makima/pull/57) | D-Pad buttons were classified as axes, making them impossible to remap |
| `x11rb::connect()` panic on Wayland after suspend | [#58](https://github.com/cyber-sushi/makima/pull/58) | Caused the worker thread to die silently; service appeared active but processed no events |
| Evdev fd reconnect on device read error | — | When the evdev stream returns an I/O error (e.g. USB hotplug), makima now reinitialises automatically instead of silently stopping |

## Sleep / resume behaviour

The Steam Deck's evdev fd freezes silently on suspend — makima receives no error and cannot self-recover. A companion service, `makima-resume-watcher.service`, watches for the `PrepareForSleep(false)` D-Bus signal from `org.freedesktop.login1` and restarts makima 2 seconds after every resume.

The watcher is bound to `makima.service` (`BindsTo=`, `WantedBy=`): it starts and stops with makima and restarts automatically if the underlying `dbus-monitor` process exits for any reason.

## Relationship to upstream

Bug fixes are submitted to upstream as PRs. Features specific to the Deckery architecture (state export, IPC, trackpad emulation) are maintained here; an upstream proposal may follow once the design stabilises.
