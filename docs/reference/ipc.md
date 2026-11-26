# IPC

Makima-deckery exposes a Unix socket at `$XDG_RUNTIME_DIR/makima-control.sock` for runtime control. Commands are newline-terminated strings.

`$XDG_RUNTIME_DIR` is `/run/user/<uid>` — a per-user tmpfs with mode `0700`, created by systemd at login. The socket lives there rather than in `/tmp` because `/tmp` is world-writable, and this socket accepts `pause`: anything able to create the path first could switch off input remapping. The per-user location also means each logged-in user gets their own socket, which is how `deckery-auth-daemon` addresses instances individually — it scans `/run/user/*/makima-control.sock`.

## Commands

| Command | Effect |
|---|---|
| `pause` | Suspend all remapping — input is still read and state is still exported, but no output events are emitted and no commands are executed |
| `resume` | Resume normal remapping |
| `gaming_mode enable` | Enable Gaming Mode — suppresses all remaps, passes raw input to the OS |
| `gaming_mode disable` | Disable Gaming Mode — returns to normal remapping |
| `config enable <name>` | Enable the named config, using its file base name (e.g. `Firefox`) — reflected immediately in `state.json` `configs[].enabled` |
| `config disable <name>` | Disable the named app-specific config — the base config remains active. On the *active* member of an exclusive group this switches the whole group off; on an inactive member it does nothing |
| `config group enable <slug>` | Switch a whole exclusive group on, restoring the member last chosen (e.g. `kde-desktop-layout`) |
| `config group disable <slug>` | Switch a whole exclusive group off — no member stays active, and the remembered choice survives for the next enable |
| `analog-state-export on` | Write analog axis values (sticks, trackpads) into `state.json` on every change |
| `analog-state-export off` | Stop writing analog values (default — reduces write frequency) |
| `override begin` / `set <path> <json>` / `clear` / `end` | The override session — see [below](#override-session). The only commands that are answered |

## Usage

```bash
echo "pause"                                        | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "resume"                                       | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "gaming_mode enable"                           | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "gaming_mode disable"                          | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "config enable Firefox"  | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "config disable Firefox" | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "config group disable kde-desktop-layout"      | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "config group enable kde-desktop-layout"       | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "analog-state-export on"                       | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "analog-state-export off"                      | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
```

The socket may not exist if makima is not running — handle gracefully (socat exits with an error, nothing else happens). The current `paused` state is always reflected in `$XDG_RUNTIME_DIR/makima-state.json`.

## HUD dry-run mode

The primary use case for `pause`/`resume` is the HUD overlay. When the HUD opens, it sends `pause` so button presses show up in the live preview without triggering real actions. When the HUD closes, it sends `resume`.

The primary use case for `analog-state-export` is the same: analog data is only written while the HUD is open (to keep the analog overlays current), and disabled again when the HUD closes to avoid unnecessary write load.

## Bindings that bypass pause

Command bindings with `no_pause = true` fire even when makima is paused. The HUD toggle binding itself must use this flag, otherwise it would be impossible to close the HUD with the controller:

```toml
[commands]
BTN_THUMBL = { run = ["deckery-hud-toggle"], no_pause = true, label = "Toggle HUD" }
```

## Override session

The onboarding tour unlocks the controller step by step, so it sets the live bindings from outside. An override session is a layer on top of the effective config — above the base config, the modules and the focused app's override, so switching windows does not escape it. When the session ends, the layer is dropped and the configs are read from disk again.

### Protocol

One line per connection, as for every command — but an override command is **answered**: makima writes one line back on the same connection, then closes it. Read the reply before you close.

| Command | Reply | Effect |
|---|---|---|
| `override begin` | `ok <id>` | Opens a session with an empty layer. Ends Gaming Mode. Ids count up from 1 with every makima start. |
| `override set <path> <json>` | `ok` | Sets `<path>` in the layer to the JSON value — see below. |
| `override clear` | `ok` | Takes every binding out: the layer's own and everything underneath (`[remap]`, `[commands]`, `[movements]`, `[hints]`). Trackpads and settings stay. The usual first step. |
| `override end` | `ok` | Ends the session: the layer is dropped, the configs are read from disk, and the device session is rebuilt, as after a config file change. |

Every failure is `error <message>`, on one line, and is also logged to the journal. A failed command changes nothing.

| Error | When |
|---|---|
| `error a session is already open (id <id>)` | `begin` while a session is open. Only one at a time. |
| `error no session is open` | `set`, `clear` or `end` without a session. |
| `error <path>: …` | A `set` that was refused: invalid JSON, a path that cannot be set, or a config the parser rejects. |
| `error usage: …` | A line that starts with `override` but is none of the above. |

```bash
echo "override begin" | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock   # → ok 1
echo "override clear" | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock   # → ok
echo 'override set remap.BTN_TR2 { "keys": ["BTN_LEFT"], "label": "Click" }' \
                      | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock   # → ok
echo 'override set trackpad.right.mode "trackball"' \
                      | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock   # → ok
echo "override end"   | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock   # → ok
```

### `set`: path and value

The layer is a config document, written as you would write a config file, only in JSON. `<path>` is a dotted path into it and must not contain spaces; the JSON is the rest of the line and may.

- The first segment is one of `remap`, `commands`, `movements`, `hints`, `settings`, `trackpad`. `device`, `module` and `gaming_mode` cannot be overridden.
- `remap` sets the whole `[remap]` table of the layer, `remap.BTN_SOUTH` one binding in it, `trackpad.right.mode` one key. A `set` replaces whatever the layer held at that path and creates the tables on the way. Keys are the config file's: device aliases (`A`, `L1-X`) work.
- Bindings in the layer win over the same button and combination underneath, exactly like an app override; everything the layer does not name is the user's — unless `clear` took it out. Setting `remap` to `{}` drops the layer's own remaps, not the user's.
- `trackpad` is merged key by key into the pad tables underneath, so `trackpad.right.mode` switches the mode and keeps that pad's `click_pressure` and KDE settings.

The layer is validated through the same code a config file goes through, and stricter: what a file only warns about is an error here. Validation is all or nothing — if anything in the resulting layer is wrong, nothing of the `set` applies. Refused are:

- invalid JSON, or `null` (TOML has no null);
- anything the config parser rejects: an unknown section or key, an unknown output key, a section that is not a table;
- a binding that names an unknown button, or a movement that is no movement;
- a trackpad mode makima does not know, or a setting its parser rejects;
- a `[commands]` entry whose command line is not bound in any loaded config. An override may bind the HUD toggle or a brightness command the configs already have, matched on the whole argument list, but never a new one.

A change to `trackpad` or `settings` rebuilds the device session, the same as a config reload — the pads reset for a moment. Bindings apply at once.

### While a session is open

- `context.override_active` is `true` in `makima-state.json`, and `bindings` shows the effective config with the layer on top — see [state.json](state-json.md#context).
- Gaming Mode is off and refused — by `gaming_mode enable`, Steam game detection and the double-click alike. The double-click trigger is switched off; QAM is an ordinary button for the session. `pause` and `resume` work as usual.
- Config file changes are not read. They apply when the session ends, which reads the files anyway.

### How a session ends

- `override end`.
- The **emergency exit**: holding Steam and QAM (···) together for 3 seconds ends the session, whatever the layer has cleared. It is built into makima and cannot be configured away.
- A makima restart: the session lives in memory only, and a new process starts without one.

There is no heartbeat and no timeout: a tour that crashes leaves its session open until one of the above.

