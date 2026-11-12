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
| `while_gaming` | bool | both | Not suppressed in Gaming Mode — active during normal use and also in Gaming Mode. Default: false. |
| `haptic` | table | both | Feedback the controller plays when the binding fires. See [`haptic`](#haptic) below. |
| `note` | string | both | Short second line the HUD shows under the label: how the action is used, not what it does (e.g. `"halten"` for push-to-talk). Kept apart from `label`, so OSD toasts stay clean. |

## Labels in the HUD

When a binding has a `label`, the HUD displays that string instead of the raw key name. This makes the overlay readable for non-technical users:

- Without label: `BTN_TL-BTN_NORTH` → `KEY_LEFTCTRL KEY_C`
- With label: `L1 + Y` → `Copy`

Labels also appear in OSD toast notifications on every action.

A `note` adds a smaller, dimmed second line under the label in the HUD — for how a binding is used rather than what it does:

```toml
L1-R5 = { keys = ["KEY_LEFTCTRL", "KEY_PAGEDOWN"], label = "Text to Speech (Ctrl+PgDn)", note = "halten" }
```

Like a label, it belongs to the action: an app override that replaces the binding drops it unless the override gives its own.

## `no_pause`

By default, all bindings are suppressed while makima is paused (e.g. when the HUD is open in dry-run mode). Setting `no_pause = true` on a command binding exempts it from this — the command fires regardless of pause state.

The HUD toggle binding itself must always use `no_pause = true`, otherwise pressing L3 while the HUD is open would do nothing.

```toml
[commands]
BTN_THUMBL = { run = ["deckery-hud-toggle"], no_pause = true, label = "Toggle HUD" }
```

## `while_gaming`

By default, all bindings are suppressed while Gaming Mode is active. Bindings tagged `while_gaming = true` are exempt — they continue to fire in Gaming Mode just as they do in normal desktop use. This is useful for bindings like the HUD toggle that need to work regardless of whether a game is running.

```toml
[commands]
BTN_THUMBL = { run = ["deckery-hud-toggle"], no_pause = true, while_gaming = true, label = "Toggle HUD" }
```

See [Gaming Mode](gaming-mode.md) for more.

## `haptic`

A binding can make the controller buzz when it fires — a tick under your finger, the way Steam ticks when a trigger used as a mouse button clicks. The shipped base config does exactly that for the mouse buttons on L2 and R2:

```toml
[remap]
L2 = { keys = ["BTN_RIGHT"], no_pause = true, silent = true, haptic = { pad = "left" } }
R2 = { keys = ["BTN_LEFT"],  no_pause = true, silent = true, haptic = { pad = "right" } }
```

`pad` is the side you feel it on: `left`, `right` or `both` (default `both`). With nothing else given, it plays the default pulse — 8 ms on, 8 ms off, three times — which was tuned on the Deck against the click buzz of Steam's Lizard Mode. To change the feel, give the pulse fields inline:

```toml
R2 = { keys = ["BTN_LEFT"], haptic = { pad = "right", duration_us = 3000, count = 1 } }
```

or a full chain, in the same form every other haptic in the config takes:

```toml
haptic = { pad = "both", chain = [{ duration_us = 8000, pause_ms = 150 }, { duration_us = 8000 }] }
```

Pulse fields and `chain` are mutually exclusive, and an unknown field is an error rather than a silent fall-back to the default — `duraton_us` would otherwise just play the default pulse. `gain_db` is accepted but has no perceptible effect on Steam Deck hardware.

When it plays:

- **On the press only.** A held key repeating, or the release, is not a click.
- **Only when the binding actually fires.** A press swallowed by pause does not buzz, unless the binding is `no_pause`. In Gaming Mode only `while_gaming` bindings fire, so only they can buzz.
- **Only for the binding it is written on.** With L1 held, `L1-R2` is a different binding from `R2` and does not borrow its tick. If no `L1-R2` exists and `R2` fires as the fallback, `R2`'s tick plays — it is `R2` that fired.
- **Modules and app overrides** carry it like a label: a binding an app replaces loses the old haptic unless the app gives its own.

