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
same name *entirely* — it is not merged into it.

The tray has an item for opening either folder, under **Controller Bindings**.

## Changing one binding

You almost never want to copy a whole file. Instead put a small `.toml` of your
own here with just the lines you want different:

```toml
# ~/.config/deckery/My Tweaks.toml
[remap]
Y = ["KEY_TAB"]
```

That file is a plain module, so it is merged into the controller's config like
any other — and **a file from this folder beats every file from the shipped
folder**, whatever the two are called and whichever kind of config they are.
Only when two files *here* claim the same button does the name decide, and
Deckery warns you about that in the tray.

Copy a whole shipped file here only when you want to own it: from that moment it
stops receiving updates.

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
| `Steam Deck Base.toml` | The controller: `[device]`, button aliases, `[gaming_mode]`, `[remap]`, `[settings]` |
| `Steam Deck Trackpads.toml` | `[trackpad]` — pad modes, haptics, KDE input settings |
| `KDE Desktop.toml`, `Hyprland Desktop.toml` | Window control, one per compositor |
| `KDE Desktop Layout *.toml` | Virtual-desktop navigation — at most one is active |
| `Voice Control.toml` | Push-to-talk |
| `apps/*.toml` | Per-application overrides |

## Who wins

Configs are layered by who wrote them:

```text
shipped modules  <  shipped base config  <  your files (modules first, base last)
```

Within one layer the alphabetically last name wins — but two shipped modules
binding the same button is treated as a **config bug**, not a feature, and
Deckery warns about it in the tray rather than picking a winner quietly. A file
of yours winning against a shipped one never warns.

Modules gated to different compositors (`requires_compositor`) never load
together, so the same binding in `KDE Desktop.toml` and `Hyprland Desktop.toml`
is not a conflict. Neither are two members of the same exclusive group.

## Exclusive groups

Modules that are alternatives to one another name a shared group:

```toml
[module]
exclusive_group = "kde-desktop-layout"
```

At most one member is active. Switching one on switches its siblings off in the
same step, and the tray draws the set as one choice rather than as separate
switches. The whole group can also be switched off, from the **Enabled** entry at
the top of its submenu — your member choice is remembered while it is off, so
switching it back on returns to the one you picked.

## preferences.toml

`preferences.toml` is the one file here that is **not** a config — it records
which modules you switched on, and nothing about what they do:

```toml
[exclusive_groups]
kde-desktop-layout = "KDE Desktop Layout Horizontal"

[groups]
disabled = []

[modules]
disabled = ["Voice Control"]
```

Deckery rewrites it whenever you toggle something in the tray. Only your
deviations are recorded — a module that appears nowhere in the file is on, which
is what lets a newly shipped module arrive already active. Editing it by hand
works, but takes effect on the next restart rather than immediately.

A group listed under `[groups] disabled` has no active member at all. Its line in
`[exclusive_groups]` stays while it is off — that is the choice to restore when
you switch it back on.

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
