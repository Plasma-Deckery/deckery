# App Config

An app config applies while a matching window is focused, on top of everything else. It overrides only what differs — every other button keeps whatever the base config and the modules gave it.

See [Configuration](../../configuration.md) for config directories, the override model, and how a file's role is determined.

## What a file is called does not matter

There is no naming convention. An app config is any file that declares a window class:

```toml
# apps/Firefox.toml
[module]
match_window_class = "firefox"

[remap]
R1-Left  = { keys = ["KEY_LEFTALT", "KEY_LEFT"],  label = "Back" }
R1-Right = { keys = ["KEY_LEFTALT", "KEY_RIGHT"], label = "Forward" }
R1-Up    = { keys = ["KEY_LEFTCTRL", "KEY_R"],    label = "Reload" }
```

The window class comes from the focused window's `resourceClass` property in KWin. It is matched by name: capitalisation is ignored and a reverse-DNS publisher prefix is dropped first, which is what lets one entry cover the different spellings Wayland and X11 report for the same application. Whole names only, so a name is never matched by a fragment of itself. A list is still accepted, for packagings that renamed the app outright.

## Config inheritance

Only the bindings listed in the app config are overridden; all other buttons continue to use the layers below it. The full merge order, lowest first:

1. Shipped plain modules, in name order (`KDE Desktop`, `Steam Deck Trackpads`, …)
2. The shipped base config (`Steam Deck Base.toml`), which declares the device and what its buttons do
3. Your own plain modules from `~/.config/deckery/`
4. Your own base config, if you took one over
5. The app config for the focused window

Your modules sit **above** the shipped base config on purpose. The bindings you
are most likely to want moved are declared there, and having to adopt that whole
file to change one of them is exactly the trade a small module of your own
avoids. A base config you wrote yourself is the exception: once nothing
distinguishes the two by authorship, the more specific statement — the file that
names the device — gets the last word again.

An app config therefore inherits bindings, settings and trackpad behaviour from several files without knowing about any of them.

## Event-driven window focus

Window focus changes are detected via a KWin D-Bus script (`kwin_watcher`), which registers `org.makima.watcher` on the session bus and receives a callback from `workspace.windowActivated` on every focus change.

This replaces the previous approach of spawning a `kdotool` subprocess on every button press to query the active window — eliminating CPU load and latency. No polling, no subprocess spawning, no external tool dependency.

## Enabling and disabling configs

App configs and modules can be toggled at runtime without restarting makima. The base config (`Steam Deck Base.toml`) is always active and cannot be toggled.

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
| `"warning"` | Config **is** loaded, and something about it is worth saying |
| `"error"` | Config could not be parsed and is **not** loaded — the entry's `errors` array has the details |

The common warning is a file of yours that failed to parse while a shipped
config of the same name exists: the shipped one stays in effect, `enabled` stays
true, and the message names the file that was skipped. A broken file of yours
with no shipped counterpart has nothing to fall back to and is an `error`.

An unknown key in `[module]`, `[device]`, `[gaming_mode]` or `[trackpad]`, or a
misspelt section name, is an `error` rather than a dropped line —
`match_window_classes` would otherwise turn an app override into a plain module
applied to every window. Button names inside `[remap]` and `[commands]` are not
restricted.

The tray appends `⚠️` to a `warning` row and `🛑` to an `error` row — after the
label, so the tree glyphs that indent a module under its base keep the start of
the line. Clicking either opens a scrollable dialog with the full message.

## Key config attributes

| Attribute | Meaning |
|---|---|
| `no_pause = true` | Binding fires even when makima is paused (e.g. HUD is open) |
| `CUSTOM_MODIFIERS` | Defines which buttons act as modifier keys in this config |
| `GRAB_DEVICE = "true"` | Enables exclusive evdev grab (`EVIOCGRAB`) for this device. **Off by default** — must be an explicit opt-in. With grab active, no other process receives events from the device node. See [deckery-controller](../deckery-controller.md) for grab details. |
