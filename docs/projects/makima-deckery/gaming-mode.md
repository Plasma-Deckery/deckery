# Gaming Mode

Makima remaps controller buttons to keyboard and mouse events. In desktop use that's exactly what you want — but when a game is running, the game already reads the controller directly. With makima's remaps active at the same time, every button press arrives twice: once as the original controller input the game reads, and once as the keyboard event makima emits. The result is double inputs — pressing D-Pad up causes both a jump (from the game reading the D-Pad) and another jump (from the arrow key makima emitted).

Gaming Mode solves this by deactivating all of makima's bindings for as long as it's active. The game gets the controller to itself.

## Activating Gaming Mode

By default, double-pressing the **QAM button** (···) toggles Gaming Mode on and off. A haptic pulse on both trackpads confirms the switch.

## Automatic detection

Makima can detect automatically when a game has been launched via Steam and activate Gaming Mode without any manual input. When the game loses focus or is closed, Gaming Mode is deactivated again.

This behaviour is on by default and can be disabled in the config:

```toml
[gaming_mode]
auto_detect_steam_games = false
```

---

For trigger config, haptic setup, IPC commands, `while_gaming` bindings, and state export fields, see the [Gaming Mode reference](../../reference/gaming-mode.md).
