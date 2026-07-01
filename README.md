# Deckery

The Steam Deck is a genuinely capable handheld computer. Deckery's goal is to get the most productive and efficient workflows out of it — making full use of the unique combination of touch, trackpads, and controller buttons on the input side, while also shaping the OS to work well in this input mode and on the small screen. The goal is fast and intuitive control of the device — without needing an external keyboard and without relying on the Steam application running.

[![Watch on YouTube](https://img.youtube.com/vi/KEW9rSAQW04/maxresdefault.jpg)](https://www.youtube.com/watch?v=KEW9rSAQW04)

## ☕ Support Deckery

Deckery is free and open-source. If you use this project or share the vision of a truly efficient Linux handheld, your support directly fuels its development.

**Current Focus:** Funding the final push to 1.0, specifically working on touchpad support and gesture integration in undocumented Steam Deck hardware features.

**How funds are used:**
- 🛠️ Dedicated development hours for feature implementation and testing
- ☕ Coffee for late-night debugging sessions
- 🏆 **Sponsor Recognition:** Monthly sponsors get their name/logo added to the `README.md`.

Every contribution brings the 1.0 release closer.


## Subprojects

Deckery is an umbrella for several subprojects. Some form the core — remapping controller buttons to system functions, with visual companion apps like the HUD and tray. Others extend KDE Plasma with configurations and additional tooling so the desktop is optimally suited for handheld use on the Steam Deck.

→ [Full documentation](https://plasma-deckery.github.io/deckery/projects/)

---

### [deckery-hud](https://github.com/Plasma-Deckery/deckery-hud)
A live overlay for visualising and exploring your button config. See what every button does right now — controls should be discoverable and explain themselves, for easier onboarding and faster recall.

<video src="https://github.com/user-attachments/assets/728cf2dc-443e-446e-8714-4931174684ad" controls autoplay loop muted></video>

---

### [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery)
The heart of Deckery — the input remapper. Reads raw evdev events directly, applies context-aware button configs, and emits keyboard/mouse events. Supports per-app layouts, modifier keys, and trackpad gesture devices.

→ [Full documentation](https://plasma-deckery.github.io/deckery/projects/makima-deckery/)

---

### [deckery-tray](https://github.com/Plasma-Deckery/deckery-tray)
System tray applet for monitoring and controlling the Deckery service stack. → [Full documentation](https://plasma-deckery.github.io/deckery/projects/deckery-tray/)

### [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles)
An opinionated KDE desktop setup tuned for the Steam Deck's screen size and input methods. → [Full documentation](https://plasma-deckery.github.io/deckery/projects/steamdeck-dotfiles/)

---

## Progress & Challenges

Current status and open challenges: [plasma-deckery.github.io/deckery/progress-and-challenges/](https://plasma-deckery.github.io/deckery/progress-and-challenges/)

---

## Setup

```bash
curl -sSL https://raw.githubusercontent.com/Plasma-Deckery/deckery/main/get.sh | bash
```

> **Reading the full installation guide is required** — the installer alone is not enough. Steam needs to be configured for coexistence with Deckery after installation.
>
> → [Setup Guide](https://plasma-deckery.github.io/deckery/setup-guide/) · [Steam Input configuration](https://plasma-deckery.github.io/deckery/setup-guide/#2-configure-steam-input-for-coexistence)

---

## Device

Tested on: Steam Deck (Bazzite 43, KDE Plasma 6, Wayland)

### Coffee
Deckery is free and open-source. If you find the project useful and want to support its ambitious goal, i would be honoured if you considered donating. Thanks :)

<p align="center">
  <a href="https://ko-fi.com/phischdev" target="_blank">
    <img src="https://storage.ko-fi.com/cdn/kofi3.png" alt="Buy Me a Coffee at ko-fi.com" height="40" />
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://github.com/sponsors/phischdev" target="_blank">
    <img src="https://img.shields.io/badge/Sponsor-%E2%9D%A4-brightgreen?style=for-the-badge&logo=github&logoColor=white" alt="Sponsor on GitHub" height="40" />
  </a>
</p>
