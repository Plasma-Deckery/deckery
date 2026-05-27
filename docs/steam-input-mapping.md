# Steam Input Desktop Config — Mapping Referenz

Quelle: `desktop_neptune.vdf` (Steam Deck Desktop Config, Default Preset)

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

| Button | Steam-Name | → Key |
|---|---|---|
| L1 | left_bumper | `KEY_LEFTCONTROL` |
| R1 | right_bumper | `KEY_LEFTALT` |
| Select (☰) | button_escape | `KEY_ESCAPE` |
| Start (≡) | button_menu | `KEY_TAB` |
| L4 | button_back_left | `KEY_LEFTWINDOWS` (Super) |
| L5 | button_back_left_upper | `KEY_LEFTSHIFT` |
| R4 | button_back_right | `KEY_PAGEDOWN` |
| R5 | button_back_right_upper | `KEY_PAGEUP` |
| Steam-Button | button_capture | `system_key_1` |

## ABXY (Gruppe 0: four_buttons)

| Button | → Key |
|---|---|
| A | `KEY_RETURN` |
| B | `KEY_ESCAPE` |
| X | `SHOW_KEYBOARD` (OSK) |
| Y | `KEY_SPACE` |

## Trigger + Trackpads

| Input | → Output |
|---|---|
| L2 (Gruppe 4, trigger) | `mouse_button RIGHT` |
| R2 (Gruppe 5, trigger) | `mouse_button LEFT` |
| Rechtes Trackpad (Gruppe 14) | absolute_mouse → Cursor |
| Rechter Stick-Click R3 (Gruppe 25) | `mouse_button LEFT` |
| Linkes Trackpad (Gruppe 26) | scrollwheel |

## Kritische Kombinationen

### L1 + R3 → Sprachsteuerung (OpenWhispr)
- L1 (left_bumper) → `KEY_LEFTCONTROL`
- R3 (right joystick click) → `mouse_button LEFT`
- Kombiniert: **Ctrl + Linksklick** = OpenWhispr Push-to-Talk Hotkey

### makima-Äquivalent (für Phase 2)
```toml
[remap]
BTN_TL      = ["KEY_LEFTCTRL"]     # L1 → Ctrl
BTN_THUMBR  = ["BTN_LEFT"]         # R3 → Linksklick
# Kombination L1+R3: Ctrl+Click wird automatisch
# gesendet wenn BTN_TL gehalten + BTN_THUMBR gedrückt
```

## D-Pad (Gruppe 9: dpad)
Pfeiltasten UP/DOWN/LEFT/RIGHT — unverändert bleiben.

## Wichtige Änderung (von uns)
- Linker Stick war: Gruppe 27 (dpad, Pfeiltasten) aktiv
- Linker Stick jetzt: Gruppe 3 (joystick_move, echte Achswerte) aktiv
- → Kando kann Joystick-Navigation nutzen
