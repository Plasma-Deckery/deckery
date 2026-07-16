# Steam Input Desktop Config — Mapping Referenz

## How Deckery handles Steam Input

Deckery disables ALL Steam Desktop Input by using Steam's own **Local Selection** mechanism. It writes a single entry into `configset_controller_neptune.vdf` (App ID 413080 — Steam's universal internal ID for the Desktop controller config) that points Steam's Desktop controller profile to its built-in `empty.vdf`, which contains no bindings at all. No sudo is required and Steam updates work normally.

The result is that Steam applies zero button mappings in desktop mode. Makima takes over full input handling instead.

## Reference: Steam's default Desktop layout

The tables below document what Steam's **default** Desktop controller layout (`desktop_neptune.vdf`) contains. None of these mappings are active when Deckery is configured — they are preserved here for reference only.

## Aktive Gruppen (Default Preset)

| group_source_binding | Hardware | Gruppe ID | Modus |
|---|---|---|---|
| switch active | Buttons (L1,R1,L4,L5,R4,R5,Start,Select,Steam) | 7 | switches |
| button_diamond active | ABXY | 0 | four_buttons |
| left_trackpad active | Linkes Trackpad | 26 | scrollwheel |
| right_trackpad active | Rechtes Trackpad | 14 | absolute_mouse |
| joystick active | Linker Stick | 3 | joystick_move |
| right_joystick active | Rechter Stick | 25 | joystick_mouse |
| left_trigger active | L2 | 4 | trigger |
| right_trigger active | R2 | 5 | trigger |
| dpad active | D-Pad | 9 | dpad |

## Button-Mappings (Gruppe 7: switches)

| Button | Steam-Name | Key |
|---|---|---|
| L1 | left_bumper | `KEY_LEFTCONTROL` |
| R1 | right_bumper | `KEY_LEFTALT` |
| Select | button_escape | `KEY_ESCAPE` |
| Start | button_menu | `KEY_TAB` |
| L4 | button_back_left | `KEY_LEFTWINDOWS` (Super) |
| L5 | button_back_left_upper | `KEY_LEFTSHIFT` |
| R4 | button_back_right | `KEY_PAGEDOWN` |
| R5 | button_back_right_upper | `KEY_PAGEUP` |
| Steam-Button | button_capture | `system_key_1` |

## ABXY (Gruppe 0: four_buttons)

| Button | Key |
|---|---|
| A | `KEY_RETURN` |
| B | `KEY_ESCAPE` |
| X | `SHOW_KEYBOARD` (OSK) |
| Y | `KEY_SPACE` |

## Trigger + Trackpads

| Input | Output |
|---|---|
| L2 (Gruppe 4, trigger) | `mouse_button RIGHT` |
| R2 (Gruppe 5, trigger) | `mouse_button LEFT` |
| Rechtes Trackpad (Gruppe 14, absolute_mouse) | Cursor-Bewegung |
| Rechter Trackpad-Click (Gruppe 14, Soft_Press) | `mouse_button LEFT` |
| Rechter Stick R3 (Gruppe 25, joystick_mouse) | Mausbewegung, kein Key-Mapping |
| Linkes Trackpad (Gruppe 26, scrollwheel) | Scroll Up/Down |

## Kritische Kombinationen

### L1 + R4 -> Sprachsteuerung (OpenWhispr)
- L1 (left_bumper) -> `KEY_LEFTCONTROL`
- R4 (button_back_right) -> `KEY_PAGEDOWN`
- Kombiniert: **Ctrl + PageDown** = OpenWhispr Push-to-Talk Hotkey

### makima-Aequivalent (fuer Phase 2)
```toml
[remap]
BTN_TL = ["KEY_LEFTCTRL"]   # L1 -> Ctrl
# R4 evdev-Code muss noch per evtest verifiziert werden
# (vermutlich BTN_C oder aehnlich fuer back paddle)
BTN_TL-<R4> = ["KEY_LEFTCTRL", "KEY_PAGEDOWN"]  # L1+R4 -> Ctrl+PageDown
```

## D-Pad (Gruppe 9: dpad)
Pfeiltasten UP/DOWN/LEFT/RIGHT - unveraendert bleiben.

## Wichtige Aenderung (von uns)
- Linker Stick war: Gruppe 27 (dpad, Pfeiltasten) aktiv
- Linker Stick jetzt: Gruppe 3 (joystick_move, echte Achswerte) aktiv
- Kando kann damit Joystick-Navigation nutzen
