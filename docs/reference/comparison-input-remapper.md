# Comparison: Makima-Deckery vs. Input Remapper

[Input Remapper](https://github.com/sezanzeb/input-remapper) is a well-established Linux input remapper with a GTK GUI, broad device support, and an active community. It is included in Bazzite (disabled by default, re-enableable via `ujust restore-input-remapper`).

This page explains how makima-deckery differs and why both tools exist.

---

## Feature comparison

| Feature | Input Remapper | Makima-Deckery |
|---|---|---|
| **Configuration** | GTK GUI + preset files | TOML text file |
| **Modifier layers / combos** | Yes (combinations) | Yes — multiple layers, triple-modifier combos |
| **Per-app configs** | No | Yes — window focus via KWin D-Bus |
| **Config inheritance** | No | Yes — app override inherits base config |
| **Shell commands as actions** | Yes (macro language) | Yes (arbitrary shell commands) |
| **Pause / preview mode** | No | Yes — HUD dry-run mode |
| **Live state export** | No | Yes — `/tmp/makima-state.json` for HUD |
| **Gaming Mode** | No | Yes — Steam auto-detection, disables remapping |
| **`while_gaming` bindings** | No | Yes |
| **Trackpad MT emulation** | No | Yes — virtual uinput touchpad devices |
| **Lizard Mode suppression** | No | Yes — hidraw heartbeat |
| **Haptic feedback** | No | Yes — configurable pulse chains per pad |
| **IMU / stick tracking** | No | Yes — exported to state.json |
| **Steam Deck back paddles** | Partial (via evdev) | Yes — BTN_GRIPL/R/L2/R2 natively |
| **HUD integration** | No | Yes — deckery-hud |
| **IPC socket** | No | Yes — `/tmp/makima-control.sock` |
| **Runs as root** | Yes | No — input group sufficient |
| **Wayland-native** | Problematic (known bugs) | Yes |
| **Language** | Python | Rust |
| **Steam Deck / handheld specific** | No — generic | Yes — Steam Deck and HHD-supported handhelds |

---

## Why not just use Input Remapper?

Input Remapper is a general-purpose remapper for any keyboard or controller. It has no concept of the Steam Deck as a device — no trackpad emulation, no Lizard Mode suppression, no Gaming Mode, no HUD integration, no state export.

Makima-deckery is one layer of a **Steam Deck-native desktop stack**. The remapping itself is only part of it. The differentiating value is the full package:

- The Steam Deck trackpads become standard system touchpads, available to libinput and gesture tools without Steam running
- Gaming Mode activates automatically when a Steam game is detected, preventing Deckery and in-game input from colliding
- The live HUD shows the full button map, active modifiers, and analog sensor values in real time
- Haptic feedback gives physical response on trackpad touch, click, and mode changes
- All of this runs without root, without Steam, and without X11

Input Remapper cannot provide any of this because it has no access to the Steam Deck hidraw interface and no integration with the rest of the Deckery stack.

---

## Can they coexist?

Yes, with care. Both tools grab evdev devices exclusively. If both are configured for the same device, only one will be active. In Bazzite, Input Remapper is disabled by default precisely to avoid conflicts with tools like makima-deckery and Steam Input. Do not run both simultaneously on the same device.
