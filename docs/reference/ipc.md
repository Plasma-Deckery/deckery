# IPC

Makima-deckery exposes a Unix socket at `/tmp/makima-control.sock` for runtime control. Commands are newline-terminated strings.

## Commands

| Command | Effect |
|---|---|
| `pause` | Suspend all remapping — input is still read and state is still exported, but no output events are emitted and no commands are executed |
| `resume` | Resume normal remapping |
| `analog-state-export on` | Write analog axis values (sticks, trackpads) into `state.json` on every change |
| `analog-state-export off` | Stop writing analog values (default — reduces write frequency) |

## Usage

```bash
echo "pause"                    | socat - UNIX-CONNECT:/tmp/makima-control.sock
echo "resume"                   | socat - UNIX-CONNECT:/tmp/makima-control.sock
echo "analog-state-export on"   | socat - UNIX-CONNECT:/tmp/makima-control.sock
echo "analog-state-export off"  | socat - UNIX-CONNECT:/tmp/makima-control.sock
```

The socket may not exist if makima is not running — handle gracefully (socat exits with an error, nothing else happens). The current `paused` state is always reflected in `/tmp/makima-state.json`.

## HUD dry-run mode

The primary use case for `pause`/`resume` is the HUD overlay. When the HUD opens, it sends `pause` so button presses show up in the live preview without triggering real actions. When the HUD closes, it sends `resume`.

The primary use case for `analog-state-export` is the same: analog data is only written while the HUD is open (to keep the analog overlays current), and disabled again when the HUD closes to avoid unnecessary write load.

## Bindings that bypass pause

Command bindings with `no_pause = true` fire even when makima is paused. The HUD toggle binding itself must use this flag, otherwise it would be impossible to close the HUD with the controller:

```toml
[commands]
BTN_THUMBL = { run = ["deckery-hud-toggle"], no_pause = true, label = "Toggle HUD" }
```
