# Configuration

Deckery's behaviour is controlled entirely through TOML config files. Every `.toml` file in a config directory is picked up automatically — nothing has to be registered anywhere.

## The two config directories

Configs are read from two places:

| Directory | What lives there |
|---|---|
| `~/.local/share/deckery/deckery/configs/` (git install)<br>`/usr/share/deckery/configs/` (RPM) | The configs Deckery ships. Replaced on every update. |
| `~/.config/deckery/` | Your own configs and overrides. Never touched by an update. |

Both directories are scanned, along with their `apps/` subdirectory. A file is identified by its base name, so **a file in your directory replaces the shipped file of the same name entirely**. To customise `KDE Desktop.toml`, copy it into `~/.config/deckery/` and edit the copy — the shipped version is then ignored, and updates leave your version alone.

To open your config folder, use **Open config folder** in the Deckery tray menu.

!!! warning "An override is a full replacement, not a patch"
    Because your file replaces the shipped one wholesale, improvements made to the shipped version in later releases will not reach you. Override only the files you actually need to change.

## What each file is

A file's role follows from its content — there is no type field and no include list:

| Content | Role |
|---|---|
| `[device]` section | **Base config.** Names the physical device it drives. |
| `[module] match_window_class` | **App override.** Applied while a matching window is focused. |
| `[module] layout = N` | **Layout module.** Applied while layout N is active. |
| None of the above | **Plain module.** Merged into every base config. |

## The shipped files

The Steam Deck configuration is deliberately spread over several files, so that customising one concern does not mean taking ownership of all of them:

| File | Contains |
|---|---|
| `Steam Deck.toml` | `[device]`, button aliases, `[gaming_mode]` — the hardware descriptor |
| `Steam Deck Bindings.toml` | `[remap]` — base buttons and the L1 layer |
| `Steam Deck Settings.toml` | `[settings]` — stick mode, sensitivity, deadzones |
| `Steam Deck Trackpad.toml` | `[trackpad]` — pad modes, haptics, KDE input settings |
| `KDE Desktop.toml`, `Hyprland Desktop.toml` | Window and workspace control, gated per compositor |
| `Voice Control.toml` | Push-to-talk binding |
| `apps/*.toml` | Per-application overrides |

To retune your trackpad haptics you copy `Steam Deck Trackpad.toml` into `~/.config/deckery/` and edit that one file. Everything else keeps receiving updates.

Gaming Mode stays in `Steam Deck.toml` rather than getting its own file: it is a device-level concern, and the merge treats the base config as the sole authority for it — Gaming Mode set in a module would be discarded silently.

### Plain modules

A plain module — `KDE Desktop.toml`, `Voice Control.toml`, `Steam Deck Bindings.toml` — is merged into every base config automatically, just by being in the directory. Delete the file, or switch it off in the tray, and its bindings go with it.

The base config sits on top of the stack: anything it binds wins over every module. Among the modules themselves the alphabetically last one wins, and any two modules binding the same button produce a warning — that overlap is a config bug, not a feature.

A module can declare `requires_compositor` to restrict itself to one desktop environment:

```toml
[module]
requires_compositor = "KDE"
```

Modules gated to different compositors never load together, so identical bindings in `KDE Desktop.toml` and `Hyprland Desktop.toml` are not a conflict.

### Exclusive groups

Some modules are alternatives to one another — three desktop layouts, say, where
exactly one should be live. A module joins such a set by naming it:

```toml
[module]
exclusive_group = "kde-desktop-layout"
```

Switching one member on switches its siblings off in the same step, so the group
can never end up with two active members or none. The tray draws the members as
radio buttons rather than checkboxes.

If you have never chosen, the alphabetically first member of the group is the
one that runs. Shipped groups are named so that the intended default sorts
first.

### Remembering your choices

Which modules you switched on lives in `~/.config/deckery/preferences.toml`,
not in the module files themselves — those describe what a module *does*, never
whether it happens to be running.

```toml
[exclusive_groups]
kde-desktop-layout = "KDE Desktop Layout Vertical"

[modules]
disabled = ["Voice Control"]
```

Deckery rewrites the file whenever you toggle something in the tray, and reads
it at startup and on every reload. Only your deviations are recorded: a module
that appears nowhere in the file is on, which is what lets a newly shipped
module arrive already active.

The installer creates the file once, at first installation, and never touches it
again — it sits in your config directory, which updates do not write to.

### App overrides

An app override is applied on top of the base config while a matching window is focused. The shipped ones live in `apps/`:

```toml
# ~/.config/deckery/apps/Firefox.toml
[module]
match_window_class = ["firefox", "org.mozilla.firefox"]

[remap]
R1-Left  = { keys = ["KEY_LEFTALT", "KEY_LEFT"],  label = "Back" }
R1-Right = { keys = ["KEY_LEFTALT", "KEY_RIGHT"], label = "Forward" }
```

## Config format

Button names come from the `aliases` table in the base config, so bindings read as `L1-Up` rather than `BTN_TL-BTN_DPAD_UP`. Kernel names keep working alongside them; combos join with `-`.

```toml
[remap]
A       = ["KEY_ENTER"]
R1-A    = { keys = ["KEY_LEFTCTRL", "KEY_N"], label = "New Chat" }

[commands]
L1-Right = { run = ["qdbus org.kde.KWin /KWin nextDesktop"], label = "Next Desktop" }
```

`label` is what the HUD overlay shows for that button. Refer to the [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) README for the full reference including layouts, trackpad modes, and gaming mode.
