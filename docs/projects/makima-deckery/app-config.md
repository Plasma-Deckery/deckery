# App Config

Config files live in `~/.config/deckery/`. The base config `Steam Deck.toml` defines the default button layout. App-specific configs override only what differs — everything else is inherited from the base config at runtime.

See [Configuration](../../configuration.md) for the general config setup and file locations.

## Naming convention

| File | When it loads |
|---|---|
| `Steam Deck.toml` | Always — the base config |
| `Steam Deck::org.mozilla.firefox.toml` | When Firefox is the focused window |
| `Steam Deck::dolphin.toml` | When Dolphin is the focused window |

The window class comes from the focused window's `resourceClass` property in KWin.

## Config inheritance

App-specific configs only need to declare the bindings that differ from the base config. Everything else is merged from `Steam Deck.toml` at runtime via `merge_base()`. No duplication required.

```toml
# Steam Deck::org.mozilla.firefox.toml
[remap]
BTN_TL-BTN_DPAD_LEFT  = ["KEY_LEFTALT", "KEY_LEFT"]   # L1+← → Back
BTN_TL-BTN_DPAD_RIGHT = ["KEY_LEFTALT", "KEY_RIGHT"]  # L1+→ → Forward
BTN_TL-BTN_DPAD_UP    = ["KEY_LEFTCTRL", "KEY_R"]     # L1+↑ → Reload

[settings]
CUSTOM_MODIFIERS = "BTN_TL-BTN_MODE"
```

Only the bindings listed here are overridden. All other buttons continue to use the base config.

## Event-driven window focus

Window focus changes are detected via a KWin D-Bus script (`kwin_watcher`), which registers `org.makima.watcher` on the session bus and receives a callback from `workspace.windowActivated` on every focus change.

This replaces the previous approach of spawning a `kdotool` subprocess on every button press to query the active window — eliminating CPU load and latency. No polling, no subprocess spawning, no external tool dependency.

## Enabling and disabling configs

App-specific configs can be toggled at runtime without restarting makima. The base config (`Steam Deck.toml`) is always active and cannot be toggled.

Via the tray's **Controller Bindings** submenu — check or uncheck a config entry. The tray sends the IPC command and the change takes effect immediately.

Via IPC directly:

```bash
echo "config enable Steam Deck::org.mozilla.firefox"  | socat - UNIX-CONNECT:/tmp/makima-control.sock
echo "config disable Steam Deck::org.mozilla.firefox" | socat - UNIX-CONNECT:/tmp/makima-control.sock
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
