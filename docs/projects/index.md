# Projects

Deckery is an umbrella for several subprojects:

## Deckery Projects

### [Deckery HUD](deckery-hud.md)

A live overlay showing what every button does right now. Controls should be discoverable and explain themselves — for easier onboarding and faster recall.

<video src="https://github.com/user-attachments/assets/728cf2dc-443e-446e-8714-4931174684ad" controls autoplay loop muted></video>

The HUD reads makima's state snapshot and renders the current button map as a GTK4 Layer Shell overlay. It communicates back to makima via the control socket to pause remapping while the overlay is open, so button presses show up in the preview rather than firing real actions.

---

### [Makima Deckery](makima-deckery/index.md)

The input remapper. Two goals:

1. **Steam independence** — read raw evdev events directly, apply the config, emit keyboard/mouse events without Steam in the loop. No need to run Steam in the background to use the desktop efficiently.
2. **Richer control** — context-aware button layouts, per-app configs, touch and scroll gestures, and automations that go beyond what Steam Input allows.

On every input event, makima writes a fully-resolved state snapshot to `/tmp/makima-state.json` for the HUD. When `LPAD/RPAD = "trackpad"` is set, it additionally exposes the trackpads as standard uinput MT devices, making them available to libinput and gesture tools. Both trackpads are also combined into a third virtual multi-touch device for gesture recognition.

---

### [Deckery Tray](deckery-tray.md)

The control panel for the entire Deckery stack, living in the KDE system tray. No terminal needed for day-to-day use.

![Deckery tray menu](../assets/tray-cropped.png)

The tray icon changes colour to reflect the current system state at a glance — green when everything runs, orange when makima is paused or a service is down, red on failure, and a cyan badge when an update is available.

The menu provides:

- **Live service status** — colour-coded dot and state label for each service
- **Pause / Resume / Restart / Stop** controls for makima — context-sensitive, only the relevant action is shown
- **Restart HUD** and **Onscreen Display toggle**
- **Open config folder** — direct access to `~/.config/makima/`
- **One-click updates** — checks GitHub on startup and hourly, installs by running `get.sh` in a terminal window

The tray also owns the systemd service hierarchy: `makima.service` and `deckery-hud.service` are both declared `PartOf=deckery-tray.service`, so starting the tray starts everything and stopping it stops everything cleanly.

---

### [Steam Deck Dotfiles](steamdeck-dotfiles/index.md)

An opinionated KDE desktop setup — scripts, panels, KWin configuration, and system settings tuned specifically for the Steam Deck's screen size and input methods. Managed via chezmoi. Proper documentation missing for now.

---

## Forked Third-Party Tools

### [Kyanite](kyanite.md)

KWin script for dynamic workspace management, patched for single-column vertical grid layout. Kyanite ensures there is always a free workspace available, so you never have to manage workspaces manually. Vertical spaces let you rotate around the short edge of the screen.

---

### [maximized-window-gaps](maximized-window-gaps.md)

KWin script for configurable gaps around maximized windows, patched for correct behaviour on the Steam Deck screen geometry. It just looks better.

---

## Third-Party Tools in Use

### [Kröhnkite](krohnkite.md)

KWin script for dynamic window tiling. With the right config, Kröhnkite can be driven entirely by controller shortcuts via makima-deckery — toggling fullscreen, switching tiling modes, and reordering layouts without a keyboard.

---

### [OpenWhispr](openwhispr.md)

On a handheld device without a physical keyboard, voice input is the practical text entry method when away from a desk. OpenWhispr is a hotkey-activated, bring-your-own-keys Whisper frontend that can also run fully locally. The steamdeck-dotfiles include an RNNoise configuration for outdoor use.

---

## Upstream Contributions

Changes contributed back to projects Deckery builds on:

| Project | PR | Description |
|---|---|---|
| cyber-sushi/makima | [#57](https://github.com/cyber-sushi/makima/pull/57) | Fix BTN_DPAD_* silently ignored in config |
| cyber-sushi/makima | [#58](https://github.com/cyber-sushi/makima/pull/58) | Fix x11rb::connect panic after suspend |
| emberian/evdev | [#178](https://github.com/emberian/evdev/pull/178) | Add BTN_GRIPL/R/L2/R2 keycodes for Steam Deck back paddles |
| MurderFromMars/Kyanite | [#3](https://github.com/MurderFromMars/Kyanite/pull/3) | Vertical grid layout for single-column workspace switching |
