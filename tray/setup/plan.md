# Wizard – Offene Punkte & Feedback-Log

## Legende
- ✅ Erledigt
- 🔲 Offen / noch zu tun
- ❌ Missverstanden / falsch gemacht → korrigiert

---

## Welcome (Seite 1)
- ✅ Reihenfolge: "Map Trackpads" an 2. Stelle (unter "Map Controller")
- ✅ Icon "Map Controller" → L1-Pill
- ✅ Icon "Map Trackpads" → `input-touchpad` System-Icon
- ✅ Icon "Live Overlay" → `view-reveal-symbolic` (Auge wie im Passwortfeld)
- ✅ Icon "Steam-independent" → `emblem-unreadable-symbolic`
- 🔲 Touchpad-Icon Größe: zu groß bei `LARGE_TOOLBAR`, nach `BUTTON` Fix jetzt zu klein — muss gleich groß wie die anderen Icons sein

---

## Components (Seite 2)
- ✅ "Steam Deck Dotfiles" → "Plasma KDE Dotfiles (coming)"
- ✅ Icon: `settings-configure` (KDE-Zahnrad)
- ✅ Icon-Farbe: amber (`#FFCA33`, CSS-Klasse `component-icon-amber`)
- ✅ "Deckery HUD" → Auge-Icon (`view-reveal-symbolic`), nicht mehr Emoji

---

## Requirements (Seite 3)
- ✅ Reload-Button komplett entfernt (war noch drin — jetzt wirklich weg)
- ✅ "Opening terminal..." Text entfernt
- ✅ Gibt jetzt plain Widget zurück (kein Footer-Tuple mehr)

---

## HUD / "Try it now" (Seite 4)
- ✅ "Try it now" in die Footer-Zone verschoben (nicht scrollt weg)
- ❌ Status-Label im Footer verursachte Extra-Abstand vor dem Next-Button → Label entfernt
- ✅ Kein Margin zwischen Scroll-Bereich und Footer mehr

---

## Tray Intro (Seite 5)
- ✅ Gelbes Warn-Icon Beschreibungstext → "Service failed or Steam overrode its Config"

---

## Tray Menu (Seite 6)
- ✅ Screenshot: `tray-cropped.png` (nicht der volle Desktop-Screenshot)
- ✅ Kein "Deckery Reference"-Button (war fälschlicherweise hinzugefügt)
- ✅ Kein Footer-Tuple — gibt plain Widget zurück
- 🔲 Bild zu verwaschen → HYPER-Fix hat es schlimmer gemacht; Bild minimal vergrößern (höhere Zielgröße, weniger Downscale-Verlust)

---

## Makima Intro (Seite 7)
- ✅ Gleiche Icons wie HUD-Seite (L1-Pill, App-Pill, Auge, ↻ Reload)
- ✅ "Deckery Reference"-Button → öffnet https://plasma-deckery.github.io/deckery/
- ✅ "Open Config Folder"-Button im Footer

---

## Setup Step 1 – Steam's On-Screen Keyboard (Seite 8)
- ✅ Tile 1 "Steam keyboard on X button": kein Apply-Button (Ist-Zustand)
- ✅ Tile 2 "Steam keyboard on Steam+X": Apply-Button, Status-Label nur sichtbar wenn Text gesetzt (conditional)
- ❌ Tile 3 "Use Plasma's on-screen keyboard" war Teil der radio_section → deaktivierte Tile 2 beim Klick
  → Tile 3 ist jetzt ein komplett unabhängiges Widget (eigene Row, eigener Configure-Button)
  → Tiles 2 und 3 können gleichzeitig aktiv sein
- ✅ Configure-Button öffnet `kcmshell5 kcm_virtualkeyboard`

---

## Setup Step 2 – Steam's Button Mapping (Seite 9)
- 🔲 Status-Text "Restart Makima to activate." nach erfolgreichem VDF-Clear löschen
- ✅ L3-Click-Handler entfernt (nur physischer L3-Druck)
- ❌ "Try it now"-Footer war immer sichtbar (nur gedimmt) → soll komplett ausgeblendet sein
  → Footer startet mit `no_show_all=True / visible=False`
  → Wird erst nach erfolgreichem VDF-Clear eingeblendet (`set_visible(True)` + `show_all()`)
- ✅ wizard.py `_swap_footer` trackt jetzt lazy Footers via `notify::visible`-Signal

---

## Right Trackpad (Seite 10)
- ✅ Zwei Optionen: "Steam trackball" (default) und "Emulate Linux Trackpad"
- 🔲 "Configure this Trackpad"-Button erscheint nach Apply immer noch nicht — show_all()-Fix in common.py greift nicht, Ursache unklar, muss neu untersucht werden

---

## Left Trackpad (Seite 11)
- ✅ Drei Optionen: "Steam scroll" (default), "Combined Gestures", "Deckery scroll" (disabled)
- 🔲 Noch nicht weiter angepasst — so lassen bis neues Feedback

---

## Globale Fixes
- ✅ Seitentitel außerhalb des Scroll-Containers (TITLES/STEP_TAGS-Dicts, wizard.py Header-Zone)
- ✅ STEP_TAG "TRANSITION FROM STEAM" bei setup_step1, setup_step2, trackpad_right, trackpad_left
- 🔲 Next-Button Hover: weder heller (#8FEDE0 war zu hell) noch dunkler (#5BC8B5 liest sich als disabled) — richtig: leicht aufgehellt (~10%), kontrolliert, nicht ausgewaschen
- ✅ `trackpads.py` → aufgeteilt in `trackpad_right.py` + `trackpad_left.py`
- ✅ `radio_section` in common.py: `no_btn`, `btn_label`, `btn_always_sensitive` hinzugefügt
- ✅ `radio_section._apply()`: aktualisiert jetzt Dot + Row-Style für ALLE Tiles (auch no_btn-Tiles)

---

## Offene / Ungeklärte Punkte
- 🔲 Left Trackpad: wartet auf Feedback
- 🔲 Steam-Config Lock → "Passwordless Steam Config Lock" (benannt, aber noch nicht im Wizard)
- 🔲 Issue #40: Config Viewer / Dry-run Makima (angelegt, Umsetzung steht aus)
