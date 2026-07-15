# Configuration

Deckery's behaviour is controlled entirely through TOML config files that live in `~/.config/makima/`. These files tell makima which buttons do what, and can vary per application.

## Config files

### Base config: `Steam Deck.toml`

The main config file for the Steam Deck. It defines the default button layout that applies whenever no app-specific config matches.

This file is symlinked from the deckery repo into place:

```
~/.config/makima/Steam Deck.toml
    → ~/.local/share/deckery/deckery/configs/Steam Deck.toml
```

Because it's a symlink into a git repo, any edits you make here are version-controlled. To customise your base layout, edit the file directly — changes are tracked automatically.

!!! warning "Customised base config requires manual merge on updates"
    When you run `git pull` to update Deckery, changes to `Steam Deck.toml` in the repo may conflict with your local edits. Git will flag these as merge conflicts that you need to resolve manually before the update can complete. This is standard git workflow, but worth being aware of before making extensive changes to the base config.

### App-specific configs: `Steam Deck::AppName.toml`

When a window belonging to a specific application is focused, makima loads the matching app config on top of the base config. These files follow the naming pattern:

```
~/.config/makima/Steam Deck::Firefox.toml
~/.config/makima/Steam Deck::Dolphin.toml
```

App-specific configs are **not** symlinked into the repo — they live directly in `~/.config/makima/` and are yours to create and edit freely. The installer updates bundled app configs on every run: before writing the new version, it backs up your existing file as `.old` (e.g. `Steam Deck::org.kde.konsole.toml.old`). Your customisations are preserved in `.old` and can be merged back manually after an update.

## Config format

Configs are written in TOML. A minimal example:

```toml
[device]
name = "Steam Deck"

[[bindings]]
key = "BTN_SOUTH"      # A button
action = "KEY_ENTER"

[[bindings]]
key = "BTN_NORTH"      # Y button
action = "KEY_F5"

[[bindings]]
key = "BTN_TL"         # L1
modifiers = []
action = { type = "command", value = "dbus-send ... Toggle" }
```

Refer to the [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) README for the full config reference including modifiers, layouts, and context switching.

## Where to find the files

| File | Location |
|---|---|
| Base config | `~/.config/makima/Steam Deck.toml` |
| App-specific configs | `~/.config/makima/Steam Deck::*.toml` |
| Versioned source | `~/.local/share/deckery/deckery/configs/` |

To open the config folder directly, use the **Open config folder** entry in the Deckery tray menu.
