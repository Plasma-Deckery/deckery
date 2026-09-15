# App Config

An app config applies while a matching window is focused, on top of everything else. It overrides only what differs — every other button keeps whatever the base config and the modules gave it.

See [Configuration](../../configuration.md) for config directories, the override model, and how a file's role is determined.

## What a file is called does not matter

There is no naming convention. An app config is any file that declares a window class:

```toml
# apps/Firefox.toml
[module]
match_window_class = ["firefox", "org.mozilla.firefox"]

[remap]
R1-Left  = { keys = ["KEY_LEFTALT", "KEY_LEFT"],  label = "Back" }
R1-Right = { keys = ["KEY_LEFTALT", "KEY_RIGHT"], label = "Forward" }
R1-Up    = { keys = ["KEY_LEFTCTRL", "KEY_R"],    label = "Reload" }
```

The window class comes from the focused window's `resourceClass` property in KWin. Several classes can be listed — Wayland and X11 often report different ones for the same application.

## Config inheritance

Only the bindings listed in the app config are overridden; all other buttons continue to use the layers below it. The full merge order, lowest first:

1. Plain modules, in name order — `Steam Deck Bindings`, `Steam Deck Trackpad`, `KDE Desktop`, …
2. The base config (`Steam Deck.toml`), which declares the device
3. The app config for the focused window

The hardware configuration is itself split across several modules, so an app config inherits bindings, settings and trackpad behaviour from different files without knowing about any of them.

## Event-driven window focus

Window focus changes are detected via a KWin D-Bus script (`kwin_watcher`), which registers `org.makima.watcher` on the session bus and receives a callback from `workspace.windowActivated` on every focus change.

This replaces the previous approach of spawning a `kdotool` subprocess on every button press to query the active window — eliminating CPU load and latency. No polling, no subprocess spawning, no external tool dependency.

## Enabling and disabling configs

App configs and modules can be toggled at runtime without restarting makima. The base config (`Steam Deck.toml`) is always active and cannot be toggled.

Via the tray's **Controller Bindings** submenu — check or uncheck a config entry. The tray sends the IPC command and the change takes effect immediately.

Via IPC directly, using the file's base name:

```bash
echo "config enable Firefox"  | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "config disable Firefox" | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
```

The enabled state is persisted across makima restarts and reflected in `state.json` under `configs[].enabled`.

## Config status

Each config in `state.json` carries a `status` field:

| Status | Meaning |
|---|---|
| `"ok"` | Config parsed and loaded without issues |
| `"warning"` | Config loaded but contains potential issues (e.g. unknown keys) |
| `"error"` | Config could not be parsed — the entry's `errors` array contains the details |

The tray renders `warning` configs with a `⚠` prefix and `error` configs with a `🛑` prefix. Clicking an error entry opens a scrollable dialog with the full error message.

## Key config attributes

| Attribute | Meaning |
|---|---|
| `no_pause = true` | Binding fires even when makima is paused (e.g. HUD is open) |
| `no_off = true` | Binding fires even in Off mode (implies `no_pause`) |
| `CUSTOM_MODIFIERS` | Defines which buttons act as modifier keys in this config |
| `GRAB_DEVICE = "true"` | Enables exclusive evdev grab (`EVIOCGRAB`) for this device. **Off by default** — must be an explicit opt-in. With grab active, no other process receives events from the device node. See [deckery-controller](../deckery-controller.md) for grab details. |
