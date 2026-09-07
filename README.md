# Deckery

The Steam Deck is a capable handheld computer — but in desktop mode, it's awkward to use without a physical keyboard. The mouse works reasonably well, but real desktop efficiency depends on shortcuts, and those simply aren't available when you're away from a desk. The Steam on-screen keyboard doesn't fill that gap. You can remap controller buttons with other tools, but that comes with its own friction: layouts are easy to forget when you're not practising them daily.

Deckery remaps controller buttons to keyboard keys, shortcuts, and actions — with per-app layouts, modifier layers, and a live overlay that shows exactly what every button does at any given moment. The goal is full desktop productivity with just the controller in hand, without requiring the Steam process to run in the background. In addition, the project includes opinionated KDE Plasma 6 configurations that better adapt the operating system to handheld use.

## YouTube Tutorial

[![Watch on YouTube](https://img.youtube.com/vi/KEW9rSAQW04/maxresdefault.jpg)](https://www.youtube.com/watch?v=KEW9rSAQW04)

## The Mission

- Get the most out of the Steam Deck as a desktop device, without a physical keyboard.
- Become fully independent from the Steam process: all buttons, triggers, trackpads and inputs from the Deck should be usable without running Steam.
- Get the most out of the trackpads — cursor movement, scrolling, gestures, and haptics that match and go beyond Steam Input, without relying on it. → [Trackpad roadmap](https://plasma-deckery.github.io/deckery/projects/makima-deckery/trackpad/)
- Build a community library of well-crafted shortcut configs for the most commonly used apps. If you have a config you're happy with, please contribute.

→ [Progress & open challenges](https://plasma-deckery.github.io/deckery/progress-and-challenges/)

## Compatibility

|  | **Bazzite 43** | **Bazzite 44** | **CachyOS Handheld** | **GNOME** | **Hyprland** |
|---|---|---|---|---|---|
| **Base** | Fedora 43, immutable | Fedora 44, immutable | Arch, rolling | — | — |
| **Kernel** | ≤ 6.17 | 7.2 | 7.x | — | — |
| **Desktop** | KDE Plasma 6 | KDE Plasma 6 | KDE Plasma 6 | GNOME | Hyprland |
| **Installation** | COPR + `rpm-ostree` | COPR + `rpm-ostree` | `get.sh` (distrobox) | — | — |
| **Controller backend** | evdev (hid-steam) | hidraw-native | hidraw-native | — | — |
| **Steam Deck** | ✅ | ✅ | ✅ | — | — |
| **Other handhelds** | ✅ HHD pre-installed | ❌ HHD → InputPlumber | ❓ untested | — | — |
| **Button remapping** | ✅ | ✅ | ✅ | — | — |
| **Per-app bindings** (window focus) | ✅ KWin D-Bus | ✅ KWin D-Bus | ✅ KWin D-Bus | ❌ | ❓ ¹ |
| **Desktop management** (workspaces, activities) | ✅ KWin D-Bus | ✅ KWin D-Bus | ✅ KWin D-Bus | ❌ | ❌ |
| **HUD overlay** | ✅ wlr-layer-shell | ✅ wlr-layer-shell | ✅ wlr-layer-shell | ❌ | ❓ untested ² |
| **Tray icon** | ✅ | ✅ | ✅ | — | — |
| **Trackpad + haptics** | ✅ | ✅ | ✅ | — | — |
| **Gaming Mode guard** | ✅ `plasma-core.target` | ✅ `plasma-core.target` | ⚠️ untested | — | ❌ |

¹ Planned: native Hyprland IPC socket (`activewindow` events on `.socket2.sock`). `zwlr_foreign_toplevel_manager_v1` has known reliability issues on Hyprland (app_id unreliable). A PoC exists in `tools/foreign-toplevel-test/` but is untested on a real Hyprland system. Tracked in [makima-deckery#36](https://github.com/Plasma-Deckery/makima-deckery/issues/36).  
² `zwlr_layer_shell_v1` is documented as supported by Hyprland — untested in practice.

<details>
<summary>Details — controller backend, per-app bindings, HUD overlay, other handhelds</summary>

**Controller backend — why it differs between Bazzite 43 and 44**

Linux kernel 7.1 changed the `hid-steam` driver
([commit `cd33a91`](https://github.com/torvalds/linux/commit/cd33a91d37eb4d7c6ce56aa7f4688066309808eb),
Vicki Pfau / Valve): opening `/dev/hidraw*` now fully unregisters the Steam Deck evdev node.
On kernel ≤ 6.17 (Bazzite 43), the evdev node stays alive alongside hidraw and makima reads
from it normally. On kernel 7.1+ (Bazzite 44, CachyOS), the evdev node disappears the moment
hidraw is opened — makima therefore reads controller input directly from the 64-byte HID reports
on the hidraw device. The hidraw interface allows multiple simultaneous readers, so there is no
conflict with Steam.

**Per-app bindings — why KDE-only**

Per-app bindings require knowing which window is active. makima detects this via the
`org.kde.kwin.Scripting` D-Bus interface — a KWin-exclusive signal (`workspace.windowActivated`).
There is no compositor-agnostic equivalent: each compositor needs its own adapter
([makima-deckery#36](https://github.com/Plasma-Deckery/makima-deckery/issues/36)).
Since all major handheld Linux distributions ship KDE Plasma as their desktop session, this is
not a practical limitation today.

**HUD overlay — why a wlroots compositor is required**

`deckery-hud` uses `gtk4-layer-shell`, which implements the `zwlr_layer_shell_v1` Wayland
protocol. This protocol is supported by KDE KWin, Hyprland, Sway, and Niri — but deliberately
not by GNOME/Mutter. Since all tested handheld distros use KDE Plasma, this is not a blocker
([deckery#55](https://github.com/Plasma-Deckery/deckery/issues/55)).

**Other handhelds — the HHD needle's eye**

On non-Steam-Deck handhelds (ROG Ally, Legion Go, AYANEO, etc.), makima needs to see a
"Steam Deck Controller" evdev node to apply its config. [HHD](https://github.com/hhd-dev/hhd)
achieved this by creating a virtual Steam Deck UHID — `hid-steam` would bind to it and expose
the expected evdev node on every handheld. One config, all devices. Bazzite 43 shipped HHD by
default. Bazzite 44 replaced HHD with
[InputPlumber](https://github.com/ShadowBlip/InputPlumber), which presents a virtual
Xbox/DualSense pad instead — no fake Steam Deck UHID, so makima's config no longer matches.
Tracked in [makima-deckery#46](https://github.com/Plasma-Deckery/makima-deckery/issues/46).

</details>

→ [Setup guide](https://plasma-deckery.github.io/deckery/setup-guide/)

## ☕ Support Deckery

Deckery is free and open-source. If you use this project or share the vision of a truly efficient Linux handheld, your support directly fuels its development.

A significant amount of development hours goes into this project. Small contributions help to get the whole thing across the finish line.

**How funds are used:**
- 🛠️ Dedicated development hours for feature implementation and testing
- ☕ Coffee for late-night debugging sessions
- 🏆 **Sponsor Recognition:** Monthly sponsors get their name/logo added to the `README.md`.
- 🎯 **Prioritization:** If you sponsor or contribute, I'm happy to prioritize your wishes for the project.

Every contribution brings the 1.0 release closer.


## Subprojects

Deckery is an umbrella for several subprojects. Some form the core — remapping controller buttons to system functions, with visual companion apps like the HUD and tray. Others extend KDE Plasma with configurations and additional tooling so the desktop is optimally suited for handheld use on the Steam Deck.

→ [Full project documentation](https://plasma-deckery.github.io/deckery/projects/)

---

### [deckery-hud](https://github.com/Plasma-Deckery/deckery-hud)
A live overlay for visualising and exploring your button config. See what every button does at any given moment — controls should be discoverable and explain themselves, for easier onboarding and faster recall.

---

### [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery)
The heart of Deckery — the input remapper. Remaps controller buttons to keyboard keys, shortcuts, and actions, with per-app layouts, modifier layers, and trackpad gesture devices.

---

### [deckery-tray](https://github.com/Plasma-Deckery/deckery-tray)
The control panel for the Deckery stack — a system tray applet that shows live service status, provides pause/resume/restart controls for makima, and handles one-click updates.

![Deckery tray menu](docs/assets/tray-cropped.png)

---

### [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles)
An opinionated KDE Plasma desktop tuned for the Steam Deck's screen size and controller input. Includes display scaling, dynamic window tiling, Steam keyboard focus fix, flat pointer acceleration, and power management — all documented and mostly scriptable for adoption in parts.

→ [Documentation](https://plasma-deckery.github.io/deckery/projects/steamdeck-dotfiles/)

---

### Forked and Third-Party Tools

Beyond its own services, Deckery pulls in and patches a set of existing KDE and desktop tools to make them work well on the Steam Deck's screen size and controller input. Some are forked to apply targeted fixes; others are used as-is. Together they form an opinionated, curated desktop environment that goes beyond what any single tool provides.

→ [Full project overview](https://plasma-deckery.github.io/deckery/projects/)

---

## Setup

```bash
curl -sSL https://raw.githubusercontent.com/Plasma-Deckery/deckery/main/get.sh | bash
```

The installer sets everything up and walks you through the Steam Input configuration interactively. Reading the setup guide is recommended.

→ [Setup Guide](https://plasma-deckery.github.io/deckery/setup-guide/)

---

<p align="center">
  <a href="https://ko-fi.com/phischdev" target="_blank">
    <img src="https://storage.ko-fi.com/cdn/kofi3.png" alt="Buy Me a Coffee at ko-fi.com" height="40" />
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://github.com/sponsors/phischdev" target="_blank">
    <img src="https://img.shields.io/badge/Sponsor-%E2%9D%A4-brightgreen?style=for-the-badge&logo=github&logoColor=white" alt="Sponsor on GitHub" height="40" />
  </a>
</p>
