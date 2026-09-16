# Your Deckery config folder

**Deckery rewrites this file on every start. Anything you type into it is lost —
your configuration goes in the `.toml` files next to it.**

This is a copy of the README that ships with Deckery, placed here so that both
you and any assistant you point at this folder can tell what the files around it
do without leaving the directory.

## Where configs come from

There are two folders, and both are read on every start:

| Folder | Whose it is |
|---|---|
| The shipped one — `/usr/share/deckery/configs/` for an RPM install, `~/.local/share/deckery/deckery/configs/` for a git install | Deckery's. Replaced on every update. |
| This one — `~/.config/deckery/` | Yours. No update ever writes to it, apart from this README. |

Both folders are scanned, along with their `apps/` subfolder. A config is
identified by its **file name**, so a file here replaces the shipped file of the
same name *entirely* — it is not merged into it, and it is not a patch. To change
one thing about the trackpads, copy `Steam Deck Trackpads.toml` here and edit the
copy; everything you did not copy keeps receiving updates.

The tray has an item for opening either folder, under **Controller Bindings**.

## What each file is

There is no type field and no list of files to register anywhere. A file's role
follows from what is in it:

| Content | Role |
|---|---|
| a `[device]` section | **Base config** — names the physical controller |
| `[module] match_window_class` | **App override** — applied while a matching window is focused |
| `[module] layout = N` | **Layout module** — applied while layout N is active |
| none of the above | **Plain module** — merged into every base config |

Dropping a new `.toml` file here is all it takes to add one. Deleting it removes
it again. Deckery notices either within a second, without a restart.

## The shipped files

| File | Contains |
|---|---|
| `Steam Deck.toml` | `[device]`, button aliases, `[gaming_mode]` — the hardware descriptor |
| `Steam Deck Buttons.toml` | `[remap]` — what every button does, plus the L1 layer |
| `Steam Deck Sticks.toml` | `[settings]` — stick mode, sensitivity, deadzones |
| `Steam Deck Trackpads.toml` | `[trackpad]` — pad modes, haptics, KDE input settings |
| `KDE Desktop.toml`, `Hyprland Desktop.toml` | Window control, one per compositor |
| `KDE Desktop Layout *.toml` | Virtual-desktop navigation — exactly one is active |
| `Voice Control.toml` | Push-to-talk |
| `apps/*.toml` | Per-application overrides |

## Who wins

The base config sits on top: anything it binds beats every module. Among the
modules the alphabetically last one wins — but two modules binding the same
button is treated as a **config bug**, not a feature, and Deckery warns about it
in the tray rather than picking a winner quietly.

Modules gated to different compositors (`requires_compositor`) never load
together, so the same binding in `KDE Desktop.toml` and `Hyprland Desktop.toml`
is not a conflict. Neither are two members of the same exclusive group.

## Exclusive groups

Modules that are alternatives to one another name a shared group:

```toml
[module]
exclusive_group = "kde-desktop-layout"
```

Exactly one member is ever active. Switching one on switches its siblings off in
the same step, and the tray draws the set as one choice rather than as separate
switches.

## preferences.toml

`preferences.toml` is the one file here that is **not** a config — it records
which modules you switched on, and nothing about what they do:

```toml
[exclusive_groups]
kde-desktop-layout = "KDE Desktop Layout Horizontal"

[modules]
disabled = ["Voice Control"]
```

Deckery rewrites it whenever you toggle something in the tray. Only your
deviations are recorded — a module that appears nowhere in the file is on, which
is what lets a newly shipped module arrive already active. Editing it by hand
works, but takes effect on the next restart rather than immediately.

## Config format

Button names come from the `aliases` table in the base config, so bindings read
as `L1-Up` rather than `BTN_TL-BTN_DPAD_UP`. Combos join with `-`, and `label` is
what the HUD overlay shows for that button.

```toml
[remap]
A    = ["KEY_ENTER"]
R1-A = { keys = ["KEY_LEFTCTRL", "KEY_N"], label = "New Chat" }

[commands]
L1-Right = { run = ["qdbus org.kde.KWin /KWin nextDesktop"], label = "Next Desktop" }
```

The full reference is at <https://plasma-deckery.github.io/deckery/configuration/>.
