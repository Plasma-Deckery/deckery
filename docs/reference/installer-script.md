# Installer Script

`install.sh` is the umbrella installer for the full Deckery stack. It is idempotent — re-running is safe and will update components to their latest version.

## What it does

1. **Clone / update sub-repos** — clones `makima-deckery` and `deckery-hud` next to the deckery repo. When running from a tagged release, each sub-repo is checked out at the **same tag** as the main repo. If a matching tag is missing in a sub-repo, the installer exits with a clear error. See [Updates](updates.md) for details on the release-pinning mechanism.

2. **Create the distrobox container** — runs `distrobox create --name deckery --image archlinux:latest`. The container is shared by all three services. On subsequent runs this step is a no-op.

3. **Build and install Makima** — delegates to `makima-deckery/install.sh`, which compiles the Rust binary inside the container and deploys it to `~/.local/bin/`.

4. **Install Deckery HUD** — delegates to `deckery-hud/install.sh`, which installs Python/GTK4 packages inside the container and links the systemd service.

5. **Install Deckery Tray** — installs Python/GTK3 packages inside the container, links the launch script to `~/.local/bin/deckery-tray`, and installs `deckery-tray.service`.

6. **Install the app icon and `.desktop` launcher** — copies the icon to the hicolor icon theme and installs a `.desktop` file so Deckery appears in the application launcher.

7. **Remove the legacy Steam Input file** — deletes `~/.config/deckery/desktop_neptune.vdf` if it is present from a previous install.

8. **Prepare the user config directory** — creates `~/.config/deckery/` if it is missing. Nothing is copied or symlinked: makima reads the shipped configs straight out of the repo and treats a user file of the same name as an override (see [Configuration](../configuration.md)).

    Installs predating that model have a copy of every shipped config sitting in the user directory. As overrides those copies shadow the shipped file forever, so they are cleared out — but as a **one-time migration**, recorded by a stamp file, and by **moving** rather than deleting:

    - A file in `~/.config/deckery/` carrying the name of a shipped config is also exactly what the documentation tells you to create in order to customise one. A sweep that ran on every update would delete the customisation it had just asked for.
    - A leftover copy and a deliberate override cannot be told apart by then, so the ambiguity is resolved by keeping the file. Everything swept lands in `~/.config/deckery/replaced-by-update/` for you to check and delete.
    - Symlinks are skipped outright. The old scheme copied, so a link is somebody's dotfile manager pointing at its own store.
    - Names that used to be shipped and are not any more are swept too. The loop enumerates what ships *today*, so without that list a copy of the old base config would survive and go on claiming the same controller.

    After the stamp is set, nothing under `~/.config/deckery/` is ever swept again.

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
