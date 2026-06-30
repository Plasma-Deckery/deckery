# Bindings

Bindings map controller buttons to output actions. The simple form is a bare array; the extended form is an inline table that supports additional attributes.

## Simple form

```toml
[remap]
BTN_SOUTH = ["KEY_ENTER"]
BTN_TL-BTN_NORTH = ["KEY_LEFTCTRL", "KEY_C"]

[commands]
BTN_THUMBL = ["deckery-hud-toggle"]
```

Keys in `[remap]` emit keyboard/mouse events. Keys in `[commands]` run shell commands or D-Bus calls. Combo bindings use `-` as separator: `BTN_TL-BTN_NORTH` means L1 held, then Y pressed.

## Extended form

```toml
[remap]
BTN_TL-BTN_NORTH = { keys = ["KEY_LEFTCTRL", "KEY_C"], label = "Copy" }

[commands]
BTN_THUMBL = { run = ["deckery-hud-toggle"], no_pause = true, label = "Toggle HUD" }
```

## Binding attributes

| Attribute | Type | Applies to | Description |
|---|---|---|---|
| `keys` | array | remap | The key output (replaces the bare array) |
| `run` | array | command | The command to execute (replaces the bare array) |
| `label` | string | both | Human-readable name exported to the HUD and OSD |
| `no_pause` | bool | command | Execute even when makima is paused (e.g. HUD open) |

## Labels in the HUD

When a binding has a `label`, the HUD displays that string instead of the raw key name. This makes the overlay readable for non-technical users:

- Without label: `BTN_TL-BTN_NORTH` → `KEY_LEFTCTRL KEY_C`
- With label: `L1 + Y` → `Copy`

Labels also appear in OSD toast notifications on every action.

## `no_pause`

By default, all bindings are suppressed while makima is paused (e.g. when the HUD is open in dry-run mode). Setting `no_pause = true` on a command binding exempts it from this — the command fires regardless of pause state.

The HUD toggle binding itself must always use `no_pause = true`, otherwise pressing L3 while the HUD is open would do nothing.

```toml
[commands]
BTN_THUMBL = { run = ["deckery-hud-toggle"], no_pause = true, label = "Toggle HUD" }
```
