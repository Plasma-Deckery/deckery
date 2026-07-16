# Installer Script

`install.sh` is the umbrella installer for the full Deckery stack. It is idempotent — re-running is safe and will update components to their latest version.

## What it does

1. **Clone / update sub-repos** — clones `makima-deckery` and `deckery-hud` next to the deckery repo. When running from a tagged release, each sub-repo is checked out at the **same tag** as the main repo. If a matching tag is missing in a sub-repo, the installer exits with a clear error. See [Updates](updates.md) for details on the release-pinning mechanism.

2. **Create the distrobox container** — runs `distrobox assemble create` using `distrobox.ini` in the repo root. The container (Arch Linux) is shared by all three services. On subsequent runs this step is a no-op.

3. **Build and install Makima** — delegates to `makima-deckery/install.sh`, which compiles the Rust binary inside the container and deploys it to `~/.local/bin/`.

4. **Install Deckery HUD** — delegates to `deckery-hud/install.sh`, which installs Python/GTK4 packages inside the container and links the systemd service.

5. **Install Deckery Tray** — installs Python/GTK3 packages inside the container, links the launch script to `~/.local/bin/deckery-tray`, and installs `deckery-tray.service`.

6. **Install the app icon and `.desktop` launcher** — copies the icon to the hicolor icon theme and installs a `.desktop` file so Deckery appears in the application launcher.

7. **Remove the legacy Steam Input file** — deletes `~/.config/makima/desktop_neptune.vdf` if it is present from a previous install.

8. **Update the default makima config** — symlinks `configs/Steam Deck.toml` to `~/.config/makima/Steam Deck.toml`. App-specific configs (e.g. `Steam Deck::org.kde.konsole.toml`) are copied from the repo on every run; the previous version is backed up as `.old` (e.g. `Steam Deck::org.kde.konsole.toml.old`) so your customisations are preserved and can be merged back manually.

After step 8, the script runs two interactive prompts (skipped in non-interactive mode):

- **Disable Steam Input** — asks whether to write the `configset_controller_neptune.vdf` entry that points Steam's Desktop controller profile to `empty.vdf`. You can always do this later via the tray.
- **Remove leftover chattr lock** — checks whether `~/.local/share/Steam/controller_base/desktop_neptune.vdf` still carries the `chattr +i` immutable flag from a previous Deckery version, and if so prompts to remove it.

## Service hierarchy

Deckery-tray manages the entire stack:

```
plasma-core.target     ← KDE-only, not active in Gamescope/Gaming Mode
    └── deckery-tray.service   ← starts on login, owns the distrobox container
            ├── makima.service         (BindsTo tray — cannot run without it)
            └── deckery-hud.service    (BindsTo tray — cannot run without it)
```

Starting the tray starts everything. Stopping it stops everything cleanly.

## Manual invocation

```bash
# First install / update — always use get.sh
bash <(curl -sSL https://raw.githubusercontent.com/Plasma-Deckery/deckery/main/get.sh)
```

`get.sh` fetches the latest release tag, checks out that tag, sets `DECKERY_RELEASE_TAG`, and then calls `install.sh`. Running `install.sh` directly without this env var skips release pinning and runs in development mode (sub-repos pull their latest main branch instead of a matching tag).
