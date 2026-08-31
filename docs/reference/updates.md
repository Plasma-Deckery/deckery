# Updates

Deckery checks for updates automatically and can install them with a single click from the system tray.

## How version detection works

The local version is determined by reading the highest git tag in the deckery repo, sorted by semantic version:

```bash
git tag --sort=-version:refname | head -1
```

This always returns the numerically greatest tag regardless of HEAD position or how many tags share the same commit — important because the repo is left in detached HEAD state after each update.

The remote version is fetched from the GitHub Releases API:

```
GET https://api.github.com/repos/Plasma-Deckery/deckery/releases/latest
```

If `local < latest`, an update is available.

## State machine

The tray menu item follows a simple state machine:

| State | Label | Clickable | Action on click |
|---|---|---|---|
| `IDLE` | Check for Updates | ✅ | Start check |
| `CHECKING` | Checking for updates… | ❌ | — |
| `UP_TO_DATE` | Up to date | ✅ | Re-check |
| `UPDATE_AVAILABLE` | Update available: vX.Y.Z — Install | ✅ | Run `get.sh` |
| `AHEAD_OF_RELEASE` | Rollback to vX.Y.Z | ✅ | Run `get.sh` |
| `ERROR` | Update check failed — retry | ✅ | Re-check |

**`AHEAD_OF_RELEASE`** fires when HEAD is not at an exact release tag but its commit timestamp is *newer* than the latest published tag — i.e. the user is running a development snapshot built from a commit that is ahead of the release. This is not treated as an error (the tray icon stays unchanged). Clicking the item runs `get.sh`, which checks out the latest release tag — effectively a rollback to the last stable release.

Version timestamps are compared using local `git log --format=%ct` on both HEAD and the latest release tag. No additional network round-trip is needed for the comparison — only the GitHub Releases API call (already made during the update check) is required.

## Auto-check schedule

- **30 seconds** after tray startup — initial check
- **Every hour** thereafter
- Error states are retried on the next auto-check interval

## Confirmation dialog

Before running `get.sh`, the tray shows a confirmation dialog to prevent accidental installs:

**Rollback** (`AHEAD_OF_RELEASE`): dialog is always shown, with `WARNING` severity (the install will overwrite local dev changes).

**Update** (`UPDATE_AVAILABLE`): the deckery repo is checked for uncommitted files via `git status --porcelain`. If dirty files are found, the dialog is shown at `WARNING` severity with the list of affected files. If the working tree is clean, the dialog is shown at `QUESTION` severity.

In both cases the dialog defaults to **Cancel** — clicking the `X` or pressing Escape does nothing.

## Update flow

Clicking "Install" opens a Konsole terminal window and runs `get.sh`:

1. `get.sh` fetches all tags from GitHub with `--force` (so re-tagged releases overwrite stale local refs)
2. Finds the highest release tag via version sort
3. Checks out that tag in the deckery repo (with `--force` to overwrite any manually modified files)
4. Exports `DECKERY_RELEASE_TAG` and calls `install.sh`
5. `install.sh` checks out the same tag in every sub-repo (`makima-deckery`, `deckery-hud`) — the three repos are always pinned to the same version
6. Builds and installs all components
7. Restarts `deckery-tray.service`, which cascades to `makima.service` and `deckery-hud.service`

The Konsole window stays open after the install (`--noclose`) so any errors are visible.

## Release pinning

All three repos are tagged with the same version on every release:

| Repo | Role |
|---|---|
| `Plasma-Deckery/deckery` | Source of truth for version; holds `get.sh` and `install.sh` |
| `Plasma-Deckery/makima-deckery` | Must have matching tag — installer errors if missing |
| `Plasma-Deckery/deckery-hud` | Must have matching tag — installer errors if missing |

If a sub-repo tag is missing, the installer prints a clear error and exits:

```
✗ ERROR: Release tag 'vX.Y.Z' not found in makima-deckery.

  This means makima-deckery has not yet published a matching release.
  All three repos must be tagged together for a release to be installable.
```
