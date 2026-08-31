# deckery-controller

**Repository:** [Plasma-Deckery/makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) — crate at `deckery-controller/`

Hardware abstraction library for the Steam Deck controller. Everything specific to the Steam Deck as a physical device lives here: evdev event streaming, suspend/resume handling, hidraw I/O for trackpad frames and haptics, Lizard Mode suppression, and the cooperative grab yield protocol. Higher-level concerns — input mapping, virtual devices, config routing — belong in the consuming binary.

Consumers: `makima-deckery` (remapper), `deckery-auth` (PIN entry grabber).

---

## Why a separate crate

Without this crate, `makima-deckery` and any future tool that needs raw controller access would each have to reimplement the same non-trivial pieces: transparent reconnect on suspend, the hidraw sysfs discovery walk, Lizard Mode heartbeat, and the D-Bus grab handoff. Extracting them into a library keeps the consuming code focused on what it actually does with the events.

---

## Reconnect / transparent healing

The Steam Deck's evdev fd freezes silently on suspend — no error, no event, just silence. On USB hotplug (cable unplug, hub power cycle) the fd returns an `I/O error`. In both cases, the library's internal `reconnecting_reader_task` handles recovery:

1. **Suspend**: watches logind `PrepareForSleep(false)` D-Bus signal, proactively closes and reopens the evdev stream on resume.
2. **Device error**: the I/O error exits the inner read loop; `reconnecting_reader_task` re-enters a retry loop (200 ms poll, 10 s timeout).
3. **On timeout**: fires `device_error_notify` so the consuming binary (makima) can signal the tray.

From the consumer's perspective the `event_rx` channel simply keeps producing events. A `ControllerEvent::Reconnected` appears after each recovery — the only required consumer action is to release any currently held virtual output keys to avoid stuck keys after resume.

**Key implementation detail:** the old `EventStream` must be dropped *before* attempting to open a new one, because a live evdev fd holds `EVIOCGRAB`. Trying to re-grab while the old fd is still alive returns `EBUSY` and wastes the entire 10 s timeout. The library handles this correctly; it only matters if you call `try_open_event_stream` directly.

---

## EVIOCGRAB — exclusive device access

Setting `grab=true` at session start calls `EVIOCGRAB` on the evdev fd. This gives the calling process exclusive access to the event stream: no other process receives events from that `/dev/input/eventN` node while the grab is active.

Makima uses `grab=true` to ensure gamepad events go only to the remapper and not to the application. `deckery-auth` uses `grab=true` during PIN entry so the controller is fully owned for the duration.

**Limitation:** `EVIOCGRAB` covers only the evdev stream, not hidraw. The hidraw node (`/dev/hidrawN`) has no equivalent exclusive-lock mechanism — any process that can open it can read raw HID reports even during an evdev grab. Access control for hidraw must be enforced at the udev/filesystem level.

---

## Cooperative grab yield protocol

When `deckery-auth` needs to grab the controller, the currently running `makima` session must release its grab first. This is coordinated via D-Bus signals — no polling, no sleep timers:

```
Interface:  org.Deckery.Controller1
Object:     /org/Deckery/Controller1
Signals:    GrabPending(device_path: str)   ← "I want to grab"
            GrabReleased(device_path: str)  ← "I'm done, grab is free"
```

**Requester** (`deckery-auth`, `grab=true`):
1. Emits `GrabPending` before the first `EVIOCGRAB` attempt — not deferred to the first `EBUSY` — so `grab=false` sessions can flush held output keys regardless of whether a conflict exists.
2. Retries `EVIOCGRAB` every 100 ms for up to 5 s.
3. On success, returns a `GrabbedHandle` RAII guard. Dropping it emits `GrabReleased` on the already-open D-Bus connection — no reconnect latency.

**Yieldable session** (`makima`, `grab=false+yieldable=true`):
- Background listener watches `GrabPending` for its device path.
- On receipt: sends `ControllerEvent::ReleaseAll` to the consumer (flush held virtual output keys).
- The evdev stream pauses automatically while another process holds `EVIOCGRAB` and resumes on its own — no further action needed.

**Full yield** (`grab=true+yieldable=true`):
- As above, plus: releases `EVIOCGRAB` on `GrabPending`, waits for `GrabReleased`, emits a new `GrabPending` before re-grabbing (to notify `grab=false+yieldable` sessions once more), then re-grabs.

The flag matrix:

| `grab` | `yieldable` | Behaviour |
|---|---|---|
| `false` | `false` | No protocol involvement |
| `false` | `true` | Flushes keys on `GrabPending`; no grab interaction |
| `true` | `false` | Requester only; emits signals, never receives them |
| `true` | `true` | Full handoff: releases and re-grabs on demand |

---

## Lizard Mode suppression

The Steam Deck controller ships in **Lizard Mode**: it emulates a mouse and keyboard by default so Steam's UI works without a dedicated driver. The library suppresses this by periodically sending HID feature report `0x87` to the hidraw fd. The heartbeat runs inside the hidraw writer task — no separate timer required in the consumer. Dropping `LizardModeHandle` stops the heartbeat and exits the writer cleanly.

Lizard Mode can be updated live without restarting the session:

```rust
session.lizard_mode.set(Some(LizardModeSuppression {
    suppress_buttons: true,
    suppress_mouse:   true,
}));
```

---

## hidraw discovery

The Steam Deck exposes three hidraw nodes per USB interface. Only one of them is the raw controller channel (the other two back the emulated keyboard and mouse). The library identifies it via sysfs: the raw controller node is the one whose sysfs path has no `input/` subdirectory.

If discovery fails — non-Steam Deck hardware, containers without `/sys` — `pad_rx`, `haptic_tx`, and `click_pressure` are all `None`. The library degrades gracefully; evdev events still flow.

---

## Related

- [API reference and protocol details](https://github.com/Plasma-Deckery/makima-deckery/blob/main/deckery-controller/README.md) — full Rust API, testing strategy, known limitations
- [makima-deckery](makima-deckery/index.md) — primary consumer
- [Trackpad architecture](makima-deckery/trackpad.md) — how hidraw PadFrames become uinput MT events
