# Configuration

Deckery's behaviour is controlled entirely through TOML config files. Every `.toml` file in a config directory is picked up automatically — nothing has to be registered anywhere.

## The two config directories

Configs are read from two places:

| Directory | What lives there |
|---|---|
| `~/.local/share/deckery/deckery/configs/` (git install)<br>`/usr/share/deckery/configs/` (RPM) | The configs Deckery ships. Replaced on every update. |
| `~/.config/deckery/` | Your own configs and overrides. Never touched by an update, apart from the README described below. |

Both directories are scanned, along with their `apps/` subdirectory. A file is identified by its base name, so **a file in your directory replaces the shipped file of the same name entirely**. To customise `KDE Desktop.toml`, copy it into `~/.config/deckery/` and edit the copy — the shipped version is then ignored, and updates leave your version alone.

Both folders open from the tray, under **Controller Bindings** — **Open my configs** and **Open shipped configs**. Customising means copying a file from the second into the first, so both are one click away.

Deckery also keeps a `README.md` in your folder covering this page in short, so the folder explains itself — to you, or to an assistant you point at it. It is rewritten from the shipped copy on every start, which is why it is the one file there that an update touches: nothing you wrote can be in it.

!!! warning "Same name means full replacement, not a patch"
    Because a file of the same name replaces the shipped one wholesale, improvements made to the shipped version in later releases will not reach you. Take over a file only when you want to own it — for a single binding, write your own small module instead.

The replacement is conditional on the file being readable. If your copy has an error, Deckery keeps the shipped version in effect and marks the entry with a ⚠ in the tray, naming the file it skipped — a broken override costs you the edit you were making, not the bindings you started from. A file of your own that has no shipped counterpart has nothing to fall back to and is reported as a hard error instead.

Deckery is strict about the fixed sections — `[module]`, `[device]`, `[gaming_mode]`, `[trackpad]`, and the section names themselves. An unknown key there is an error rather than a line that is quietly dropped, because the alternative is worse than it sounds: `match_window_classes` instead of `match_window_class` used to turn an app override into a plain module that applied to *every* window. Button names inside `[remap]` and `[commands]` are of course not restricted.

## Changing one binding

Copying a whole file to change one line is a bad trade, and it is not necessary. Put a small `.toml` of your own in `~/.config/deckery/`, with nothing in it but the lines you want different:

```toml
# ~/.config/deckery/My Tweaks.toml
[remap]
Y = ["KEY_TAB"]
```

It is a plain module, so it is merged into the controller's config like any other. What makes it reliable is that configs are layered by **who wrote them**, not by what kind of file they are:

```text
shipped modules  <  shipped base config  <  your own files
```

A file named `My Tweaks.toml` wins against `Steam Deck Base.toml` for the same reason `Zebra.toml` would — not because of where it sits in the alphabet, but because of which folder it sits in. Your module sits above the shipped base config on purpose: the bindings you are most likely to want moved are declared there, and having to adopt that whole file to change one of them is exactly the trade this avoids.

The alphabet only settles ties inside one layer, and two of *your* files claiming the same button still produces a warning. Your file beating a shipped one does not: that is the mechanism working.

The one exception is a base config you took over yourself. Once `Steam Deck Base.toml` is your file too, nothing distinguishes the two by authorship any more, and the base config — the more specific statement, the one that names the device — gets the last word again.

## What each file is

A file's role follows from its content — there is no type field and no include list:

| Content | Role |
|---|---|
| `[device]` section | **Base config.** Names the physical device it drives. |
| `[module] match_window_class` | **App override.** Applied while a matching window is focused. |
| None of the above | **Plain module.** Merged into every base config. |

## The shipped files

The Steam Deck configuration is split where the split buys something. Buttons, sticks and Gaming Mode sit in the base config together, because a controller without a button layout is a dead controller — there is nothing to gain from switching them off separately. Trackpads and the desktop bindings are their own modules, because "off" is a real answer for both:

| File | Contains |
|---|---|
| `Steam Deck Base.toml` | The controller — `[device]`, aliases, `[gaming_mode]`, `[remap]`, `[settings]` |
| `Steam Deck Trackpads.toml` | `[trackpad]` — pad modes, haptics, KDE input settings |
| `KDE Desktop.toml`, `Hyprland Desktop.toml` | Window control, gated per compositor |
| `KDE Desktop Layout *.toml` | Virtual-desktop navigation — Horizontal, Vertical or Grid, at most one active |
| `Voice Control.toml` | Push-to-talk binding |
| `apps/*.toml` | Per-application overrides |

To retune your trackpad haptics you copy `Steam Deck Trackpads.toml` into `~/.config/deckery/` and edit that one file — it is the most-tuned config Deckery ships, and the one where owning the whole file is a fair price.

Gaming Mode has to live in `Steam Deck Base.toml`: the merge treats the base config as the sole authority for it, so Gaming Mode set in a module would be discarded silently.

### Plain modules

A plain module — `KDE Desktop.toml`, `Voice Control.toml`, `Steam Deck Trackpads.toml` — is merged into every base config automatically, just by being in the directory. Delete the file, or switch it off in the tray, and its bindings go with it.

The shipped base config sits above the shipped modules: anything it binds wins over what they provide. Your own modules sit above both, as described under [Changing one binding](#changing-one-binding). Within one of those layers the alphabetically last name wins, and two shipped modules binding the same button produce a warning — that overlap is a config bug, not a feature.

A module can declare `requires_compositor` to restrict itself to one desktop environment:

```toml
[module]
requires_compositor = "KDE"
```

Modules gated to different compositors never load together, so identical bindings in `KDE Desktop.toml` and `Hyprland Desktop.toml` are not a conflict.

### Two base configs for one controller

Base configs do not layer. makima walks them and opens the first evdev device each one matches, so two declarations covering the same controller both find it — and which of them ends up driving it is not defined. The losing config's bindings are simply absent, with nothing in either file to explain why.

Deckery reports that pair as a warning naming both files. The usual cause is a copy of a base config left in `~/.config/deckery/` under a name that is no longer shipped: it is still a valid base config and still names the same hardware. `install.sh` moves the retired names it knows about into `~/.config/deckery/replaced-by-update/`, once, as part of migrating off the old copy scheme — a base config you wrote and named yourself is yours to resolve.

### Exclusive groups

Some modules are alternatives to one another — three desktop layouts, say, where
exactly one should be live. A module joins such a set by naming it:

```toml
[module]
exclusive_group = "kde-desktop-layout"
```

Switching one member on switches its siblings off in the same step, so the group
can never end up with two active members. The tray draws the members as radio
buttons rather than checkboxes, inside a submenu named after the active one
("KDE Desktop Layout: Vertical"). Two members binding the same button is not a
conflict — that is the whole point of the group.

A group can also be switched off entirely, through the **Enabled** item at the
top of that submenu. This is deliberately not a member choice: the picked member
is remembered while the group is off, so switching it back on returns there
instead of resetting to the alphabetically first one. That preference is kept in
`[groups] disabled` in `preferences.toml`, next to the `[exclusive_groups]` line
that records the choice.

The one shipped group is `kde-desktop-layout`, which decides how `L1` + the DPad
moves between virtual desktops:

| Module | `L1` + DPad | `L1`+`R1` + DPad |
|---|---|---|
| **KDE Desktop Layout Horizontal** (default) | Left/Right switch desktop, Up/Down switch Activity | moves the window along the same axes |
| **KDE Desktop Layout Vertical** | Up/Down switch desktop, Left/Right switch Activity | moves the window along the same axes |
| **KDE Desktop Layout Grid** | all four directions move across the desktop grid | carries the window across the grid |

Horizontal is the default because it matches the single-row desktop arrangement
KDE and Bazzite ship. Grid expects you to have configured rows under **System
Settings → Virtual Desktops**, and spends all four directions on the grid, so it
has no Activity bindings.

Everything that does not depend on the arrangement — maximize, close, window
menu, the desktop overview — stays in `KDE Desktop.toml` and is unaffected by
the choice.

### Remembering your choices

Which modules you switched on lives in `~/.config/deckery/preferences.toml`,
not in the module files themselves — those describe what a module *does*, never
whether it happens to be running.

```toml
[exclusive_groups]
kde-desktop-layout = "KDE Desktop Layout Horizontal"

[modules]
disabled = ["Voice Control"]
```

Deckery rewrites the file whenever you toggle something in the tray, and reads
it at startup and on every reload. It is machine state rather than something to
edit: the file watcher deliberately skips it, so a change made by hand is not
noticed the way a change to a config file is. Only your deviations are recorded
— a module that appears nowhere in the file is on, which is what lets a newly
shipped module arrive already active.

Deckery creates the file at the first start that does not find one, by copying
the shipped `preferences.toml` into your config directory. After that it is
yours — updates never write to that directory, so your choices survive them
untouched. The copying happens in Deckery rather than in `install.sh` because an
RPM install never runs that script, and those users would otherwise start with
no recorded defaults at all.

The shipped copy fills in the exclusive-group defaults only. On/off modules are
left out, so a release that changes one of those defaults still reaches you.

If a group has no recorded choice at all, the alphabetically first member runs.
That is a safety net against an empty group, not a statement of intent — the
intended default is the one the shipped file names.

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
