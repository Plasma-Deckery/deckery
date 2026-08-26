# VM Testing

Scripts for testing Deckery in a Bazzite 44 QEMU virtual machine with live Steam Controller passthrough.

## Setup

**VM disk:** `/home/philipp/VMs/bazzite-test/install-disk.qcow2`  
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
  /home/philipp/VMs/bazzite-test/install-disk.qcow2

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
