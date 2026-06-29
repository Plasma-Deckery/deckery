# Installer Script

`install.sh` is the umbrella installer for the full Deckery stack. It is idempotent — re-running is safe and will update components to their latest version.

## What it does

1. **Clone / update sub-repos** — clones `makima-deckery` and `deckery-hud` next to the deckery repo, or pulls the latest if already present.

2. **Create the distrobox container** — runs `distrobox assemble create` using `distrobox.ini` in the repo root. The container (Arch Linux) is shared by all three services. On subsequent runs this step is a no-op.

3. **Build and install Makima** — delegates to `makima-deckery/install.sh`, which compiles the Rust binary inside the container and deploys it to `~/.local/bin/`.

4. **Install Deckery HUD** — delegates to `deckery-hud/install.sh`, which installs Python/GTK4 packages inside the container and links the systemd service.

5. **Install Deckery Tray** — installs Python/GTK3 packages inside the container, links the launch script to `~/.local/bin/deckery-tray`, and installs `deckery-tray.service`.

6. **Install the app icon and `.desktop` launcher** — copies the icon to the hicolor icon theme and installs a `.desktop` file so Deckery appears in the application launcher.

7. **Copy the Steam Input config** — copies `desktop_neptune.vdf` to Steam's controller config directory if it differs from what's already there.

8. **Link the default makima config** — symlinks `configs/Steam Deck.toml` to `~/.config/makima/Steam Deck.toml`. App-specific configs are copied once and not overwritten on subsequent runs.

## Service hierarchy

Deckery-tray manages the entire stack:

```
deckery-tray.service   ← starts on login, owns the distrobox container
    ├── makima.service         (PartOf tray — stops and restarts with it)
    └── deckery-hud.service    (PartOf tray — stops and restarts with it)
```

Starting the tray starts everything. Stopping it stops everything cleanly.

## Manual invocation

```bash
# First install
git clone https://github.com/Plasma-Deckery/deckery.git ~/.local/share/deckery/deckery
bash ~/.local/share/deckery/deckery/install.sh

# Update
cd ~/.local/share/deckery/deckery && git pull && bash install.sh
```
