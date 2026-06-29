# Pause/Resume IPC for Makima Preview

## Goal

When the HUD is open, Makima should continue to read input, update modifiers, track layout changes, and keep exporting state, but it should not emit real output events to the virtual device or launch commands.

This gives us a safe live preview mode:

- HUD open: input is processed internally, but nothing is sent outward.
- HUD closed: Makima resumes normal output.
- State export remains live so the HUD can show the latest internal state.

## Current Code Anchors

### `src/main.rs`

Makima starts in `main()` and delegates to `start_monitoring_udev(...)`. This is the top-level entry for wiring a global pause state or a control listener.

### `src/udev_monitor.rs`

`launch_tasks(...)` creates the `EventReader` per device and owns the `Arc` state that is shared across tasks. This is the cleanest place to create and share a global pause flag if we want one per Makima process.

### `src/event_reader.rs`

This is the core control path.

Relevant functions:

- `start()` starts all loops.
- `event_loop()` receives input events.
- `convert_event()` routes events into remaps, commands, movements, layout switching, or default forwarding.
- `emit_event()` writes remapped output to `virt_dev`.
- `emit_nonmapped_event()` writes unhandled events to `virt_dev` and also toggles modifier state.
- `spawn_subprocess()` runs shell commands.
- `emit_movement()` writes cursor/scroll motion.
- `toggle_modifiers()` updates the tracked modifier set.
- `write_state()` exports `/tmp/makima-state.json`.

The pause gate must live at the emission boundary, not in the input reader.

### `src/state_export.rs`

This module already owns the state serialization. It currently exports:

- `context.config_stack`
- `context.layout`
- `bindings`
- `modifier_active`

This is the right place to add:

- `paused`
- `last_event`

## Intended Behavior

### 1. Internal state keeps running

Even when paused, Makima should still:

- update `self.modifiers`
- update `current_config`
- update `active_layout`
- update `modifier_active`
- keep writing state to `/tmp/makima-state.json`

### 2. Output is suppressed at the end

When paused, Makima must skip only the side effects:

- `virt_dev.keys.emit(...)`
- `virt_dev.axis.emit(...)`
- `virt_dev.abs.emit(...)`
- `spawn_subprocess(...)`
- cursor/scroll emission

### 3. Last event remains visible

The state should still show the most recent processed input event so the HUD can act as a live preview of what Makima just saw.

## Proposed IPC Contract

Use a Unix socket for control:

- Socket path: `/tmp/makima-control.sock`
- Commands:
  - `pause`
  - `resume`

### Semantics

- `pause` sets a boolean flag that suppresses output only.
- `resume` clears that flag.
- The socket is lightweight and local to the current session.

## HUD / Launcher Integration

The external HUD launcher should be the place that sends these commands.

Lifecycle:

- before opening the HUD: send `pause`
- after closing the HUD: send `resume`

That keeps the UI layer dumb and avoids mixing input logic with frontend state.

## Recommended Implementation Order

### Step 1: Add shared pause state

Add an `Arc<Mutex<bool>>` or equivalent shared flag in the Makima runtime.

Best placement:

- create it in `launch_tasks(...)`
- pass it into `EventReader::new(...)`

### Step 2: Add `last_event` state

Track the last processed event and its interpreted action.

Suggested shape:

```rust
pub struct LastEvent {
    pub input: String,
    pub action: Vec<String>,
    pub kind: String,
    pub value: i32,
}
```

### Step 3: Add the control socket listener

Start a small async task from Makima that:

- binds `/tmp/makima-control.sock`
- accepts a line-based command
- sets or clears the pause flag

### Step 4: Gate only the output path

Wrap the final emission and command-launch points with `if !paused` checks.

Important: do not block the parts that update modifiers or the state export.

### Step 5: Export paused state

Extend the JSON export with:

- `paused`
- `last_event`

### Step 6: Update the HUD launcher

The launcher should send the IPC command and then continue with the existing open/close behavior.

## Risks / Things to Watch

- Do not pause too early. If the input pipeline is halted before modifier tracking, the HUD loses its live preview.
- Do not emit pause state only inside the HUD. The control must live in Makima or a small external launcher helper.
- Make the socket tolerant of missing or stale files so the HUD can still open before Makima is ready.
- If the HUD restarts, the pause flag should be idempotent.

## Acceptance Criteria

- HUD open while buttons are pressed does not emit real actions.
- Modifier state still changes internally.
- `/tmp/makima-state.json` keeps updating.
- The HUD can show the last event and the current preview state.
- Closing the HUD restores normal Makima output.

## Preferred Long-Term Shape

For the prototype, a Unix socket is sufficient.

Later, if we want lower latency and tighter lifecycle control, the same contract can move to a persistent control daemon or a more structured IPC channel. The pause/resume semantics should stay the same.
