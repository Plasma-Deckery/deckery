# Development

All Deckery service repos are installed by `get.sh` into `~/.local/share/deckery/`. That directory is also where development happens — there is no separate dev checkout. Edit files in place and redeploy.

## Build environment

Builds run inside the `deckery` [Distrobox](https://distrobox.it/) container (Arch Linux). The container is created during initial setup and shared across all Deckery repos.

## Compiled repos (makima-deckery)

```
~/.local/share/deckery/makima-deckery/
```

Edit the source, then run:

```bash
./redeploy.sh
```

This builds the binary inside the `deckery` distrobox container, copies it to `~/.local/bin/makima`, and restarts `makima.service` — all in one step.

## Interpreted repos (deckery-hud)

```
~/.local/share/deckery/deckery-hud/
```

The launcher scripts are symlinked directly from the repo into `~/.local/bin/` by `install.sh`. There is no build step — edits take effect after a service restart:

```bash
systemctl --user restart deckery-hud.service
```

## Config

`~/.config/makima/` is never touched by a redeploy or service restart. Config changes take effect when makima reads the file — either on startup or via the IPC socket (`resume` command).
