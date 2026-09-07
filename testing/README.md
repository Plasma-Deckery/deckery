# VM Testing

Scripts for testing Deckery in QEMU virtual machines with live Steam Controller passthrough.

Two VMs are supported:

| VM | Distro | SSH port | User | Scripts prefix |
|----|--------|----------|------|----------------|
| Bazzite 44 | Fedora/Bazzite | `localhost:2222` | `liveuser` | `vm-start.sh`, `controller-*.sh` |
| CachyOS Handheld | Arch/CachyOS | `localhost:2224` | `deck` | `cachyos-*.sh` |

All scripts look for the VM images under `~/VMs`. Set `VM_ROOT` to point
somewhere else, e.g. `VM_ROOT=/mnt/data/vms bash testing/vm-start.sh`.

---

## CachyOS Handheld VM

**VM disk:** `~/VMs/cachyos-test/install-disk.qcow2`  
**Snapshots:** `snap-cachyos-clean`, `snap-cachyos-kde-ready`, `snap-cachyos-gamescope-venus`, `snap-cachyos-deckery-main`  
**SSH key:** `~/.ssh/vm_key` (ed25519, no passphrase)  
**SSH:** `localhost:2224`, user `deck`

### Scripts

| Script | What it does |
|--------|-------------|
| `cachyos-vm-start.sh` | Start the CachyOS VM with GTK display |
| `cachyos-plymouth-fix.sh` | Kill plymouthd after every boot (required, see below) |
| `cachyos-controller-attach.sh` | Pass Steam Controller from host → CachyOS VM |
| `cachyos-controller-detach.sh` | Return Steam Controller from CachyOS VM → host |

### Typical test session

```bash
# 1. Start VM
bash testing/cachyos-vm-start.sh

# 2. Wait for SSH
until SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never \
  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no \
  -o StrictHostKeyChecking=no -o ConnectTimeout=3 -p 2224 \
  deck@localhost "echo up" 2>/dev/null; do sleep 5; done

# 3. Kill Plymouth (ALWAYS required after boot — see Known Issues)
bash testing/cachyos-plymouth-fix.sh

# 4. Pass controller to VM
bash testing/cachyos-controller-attach.sh

# 5. Return controller to host when done
bash testing/cachyos-controller-detach.sh
```

### Deploying a new makima-deckery build

```bash
# In the VM, run redeploy.sh (builds inside the 'deckery' distrobox):
SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never \
  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no \
  -o StrictHostKeyChecking=no -p 2224 deck@localhost \
  "bash ~/makima-deckery/redeploy.sh"
```

### Known issues — CachyOS VM

- **Plymouth hangs after every boot** (`plymouth-quit.service` times out).  
  `plymouthd` holds the DRM device (virtio-vga); KDE is running behind it but invisible.  
  Fix: always run `cachyos-plymouth-fix.sh` after boot.

- **`qdbus` not installed** (Qt 6-only distro; `qdbus6` is the replacement).  
  The installer (`makima-deckery/install.sh`) creates `~/.local/bin/qdbus → qdbus6` automatically.  
  Without this, all `run = ["qdbus ..."]` actions in deckery configs silently fail.

- **Display manager:** CachyOS uses `plasmalogin` (not SDDM). Autologin as `deck` into a Wayland session. `kwin_wayland` starts as a child of `startplasma-wayland`, not via systemd.

---

## Bazzite 44 VM

## Setup

**VM disk:** `~/VMs/bazzite-test/install-disk.qcow2`  
**Snapshot (clean, no Deckery):** `snap-bazzite44-clean`  
**SSH key:** `~/.ssh/vm_key` (ed25519, no passphrase)  
**SSH port:** `localhost:2222`, user `liveuser`

## Scripts

| Script | What it does |
|--------|-------------|
| `vm-start.sh` | Start the Bazzite 44 VM with GTK display |
| `controller-attach.sh` | Pass Steam Controller from host → VM |
| `controller-detach.sh` | Return Steam Controller from VM → host |

```bash
chmod +x testing/*.sh
```

## Typical test session

```bash
# 1. Start VM (opens a GTK window on the host desktop)
bash testing/vm-start.sh

# 2. Wait for SSH
until SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never \
  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no \
  -o StrictHostKeyChecking=no -o ConnectTimeout=3 -p 2222 \
  liveuser@localhost "echo up" 2>/dev/null; do sleep 5; done

# 3. Check Deckery services
ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no \
  -o StrictHostKeyChecking=no -p 2222 liveuser@localhost \
  "systemctl --user status deckery-tray.service deckery-hud.service makima.service --no-pager"

# 4. Pass controller to VM (to activate makima and the HUD)
bash testing/controller-attach.sh

# 5. Return controller to host when done
bash testing/controller-detach.sh
```

## Installing Deckery (fresh from clean snapshot)

```bash
# Restore clean snapshot (VM must be stopped)
qemu-img snapshot -a snap-bazzite44-clean \
  ~/VMs/bazzite-test/install-disk.qcow2

# Start VM, then:
ssh ... liveuser@localhost "sudo dnf5 copr enable phischx/Deckery -y"
ssh ... liveuser@localhost "sudo rpm-ostree install deckery"
ssh ... liveuser@localhost "sudo rpm-ostree rollback --reboot"
# Wait for reboot, then verify:
ssh ... liveuser@localhost "rpm -q deckery deckery-tray deckery-hud makima-deckery"
```

## Makima config (minimum to start makima in VM)

Without a config dir, makima waits (polling every 2 s) until one appears. Create a minimal one after the controller is attached:

```bash
ssh ... liveuser@localhost '
  mkdir -p ~/.config/deckery
  printf "[settings]\nGRAB_DEVICE = \"false\"\n\n[remap]\n" \
    > ~/.config/deckery/"Valve Software Steam Controller.toml"
  systemctl --user restart makima.service
'
```

After this, makima writes `/tmp/makima-state.json` and the HUD becomes active.

## Known issues (as of 0.3.0)

- **#57** — Tray icon is blank, colored dot-icons not rendered  
  Root cause: `_DIR` path calculation in `deckery-tray.py` resolves to `/usr/lib/` instead of `/usr/lib/deckery-tray/` when installed, so icons are looked up at the wrong path.

- **#58** — `steam_bridge` logs a WARNING every 2 s when Steam is running but no user is logged in  
  Root cause: poll loop doesn't distinguish "Steam not logged in yet" from "unexpected missing file".

## Notes

- The GTK window (`-display gtk`) is required — VNC captures the VGA framebuffer, which KDE Wayland doesn't render to (it uses DRM/KMS). The GTK display backend shows the virtual framebuffer directly on the host desktop.
- While the controller is in the VM, the host Steam Deck cannot use it. Switch back with `controller-detach.sh`.
- `makima.service` waits (polling every 2 s) until `~/.config/deckery/` appears — the tray seeds it on first run. The HUD needs makima's `/tmp/makima-state.json` to show anything.
- The QEMU monitor socket (`monitor.sock`) is what makes dynamic controller passthrough possible. It must exist — i.e. the VM must be running.
