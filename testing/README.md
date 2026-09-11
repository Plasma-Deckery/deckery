# VM Testing

Scripts for testing Deckery in QEMU virtual machines with live Steam Controller passthrough.

Two VMs are supported:

| VM | Distro | SSH port | User | Start script |
|----|--------|----------|------|--------------|
| Bazzite 44 | Fedora/Bazzite (rpm-ostree) | `localhost:2222` | `liveuser` | `vm-start.sh` |
| CachyOS Handheld | Arch/CachyOS (source install) | `localhost:2224` | `deck` | `cachyos-vm-start.sh` |

All scripts look for VM images under `~/VMs`. Override with `VM_ROOT=/other/path bash testing/vm-start.sh`.

---

## Bazzite 44 VM

**VM disk:** `~/VMs/bazzite-test/install-disk.qcow2`  
**UEFI vars:** `~/VMs/bazzite-test/OVMF_VARS.qcow2`  
**Snapshot (clean, no Deckery):** `snap-bazzite44-clean`  
**SSH:** `localhost:2222`, user `liveuser`, key `~/.ssh/vm_key`  
**Deckery version:** 0.4.0-1 (rpm-ostree, from `phischx/Deckery-beta` COPR)

### Scripts

| Script | What it does |
|--------|-------------|
| `vm-start.sh` | Start VM with GTK display + touch support |
| `controller-attach.sh` | Pass Steam Controller host → Bazzite VM |
| `controller-detach.sh` | Return Steam Controller Bazzite VM → host |

### Typical test session

```bash
# 1. Start VM
bash testing/vm-start.sh

# 2. Wait for SSH
until SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never \
  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no \
  -o StrictHostKeyChecking=no -o ConnectTimeout=3 -p 2222 \
  liveuser@localhost "echo up" 2>/dev/null; do sleep 5; done

# 3. Check Deckery services
SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never \
  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no \
  -o StrictHostKeyChecking=no -p 2222 liveuser@localhost \
  "systemctl --user status deckery-tray deckery-hud makima --no-pager"

# 4. Pass controller to VM (activates makima + HUD)
bash testing/controller-attach.sh

# 5. Return controller to host when done
bash testing/controller-detach.sh
```

### Installing / updating Deckery via rpm-ostree

```bash
# Enable beta COPR (builds on every push to main), disable stable
ssh ... liveuser@localhost "sudo dnf5 copr enable phischx/Deckery-beta -y"
ssh ... liveuser@localhost "sudo dnf5 copr disable phischx/Deckery -y"

# Install (first time) or upgrade
ssh ... liveuser@localhost "sudo rpm-ostree install deckery"   # first time
ssh ... liveuser@localhost "sudo rpm-ostree upgrade"            # update

# Reboot into new deployment
ssh ... liveuser@localhost "sudo systemctl reboot"
# If GRUB boots wrong deployment:
ssh ... liveuser@localhost "sudo rpm-ostree rollback --reboot"
```

### Restoring the clean snapshot

```bash
# VM must be stopped first
SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never \
  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no \
  -o StrictHostKeyChecking=no -p 2222 liveuser@localhost \
  "sudo systemctl poweroff"
sleep 10
qemu-img snapshot -a snap-bazzite44-clean ~/VMs/bazzite-test/install-disk.qcow2
```

### Known quirks — Bazzite VM

- **Touch → click:** `vm-start.sh` sets `GDK_BACKEND=x11 GDK_CORE_DEVICE_EVENTS=1` on the host before starting QEMU. Without these, touch only hovers — no click events reach the VM.

- **Invisible cursor:** Fixed once, persistent. `KWIN_FORCE_SW_CURSOR=1` is set in `~/.config/plasma-workspace/env/kwin-sw-cursor.sh` inside the VM disk. KWin 6.7+ tries hardware cursor on virtio-vga (unsupported) → invisible without this.

- **GRUB boots wrong deployment after `rpm-ostree install`:** QEMU doesn't honour GRUB's BootNext. Fix: `sudo rpm-ostree rollback --reboot`.

- **GTK display required:** VNC only shows the VGA framebuffer; KDE Wayland renders via DRM/KMS (virtio-vga), which the GTK backend forwards correctly.

---

## CachyOS Handheld VM

**VM disk:** `~/VMs/cachyos-test/install-disk.qcow2`  
**UEFI vars:** `~/VMs/cachyos-test/OVMF_VARS.fd`  
**Snapshots:** `snap-cachyos-clean`, `snap-cachyos-kde-ready`, `snap-cachyos-deckery-main`  
**SSH:** `localhost:2224`, user `deck`, key `~/.ssh/vm_key`  
**Deckery:** source install via `get.sh` / `install.sh` + distrobox

### Scripts

| Script | What it does |
|--------|-------------|
| `cachyos-vm-start.sh` | Start VM with GTK display + touch support |
| `cachyos-plymouth-fix.sh` | Kill plymouthd after boot (always required) |
| `cachyos-controller-attach.sh` | Pass Steam Controller host → CachyOS VM |
| `cachyos-controller-detach.sh` | Return Steam Controller CachyOS VM → host |

### Typical test session

```bash
# 1. Start VM
bash testing/cachyos-vm-start.sh

# 2. Wait for SSH
until SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never \
  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no \
  -o StrictHostKeyChecking=no -o ConnectTimeout=3 -p 2224 \
  deck@localhost "echo up" 2>/dev/null; do sleep 5; done

# 3. Kill Plymouth (ALWAYS required — see Known Quirks)
bash testing/cachyos-plymouth-fix.sh

# 4. Pass controller to VM
bash testing/cachyos-controller-attach.sh

# 5. Return controller to host when done
bash testing/cachyos-controller-detach.sh
```

### Deploying a new makima-deckery build

```bash
SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never \
  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no \
  -o StrictHostKeyChecking=no -p 2224 deck@localhost \
  "cd ~/.local/share/deckery/makima-deckery && git pull && bash redeploy.sh"
```

### Known quirks — CachyOS VM

- **Plymouth hangs after every boot:** `plymouthd` holds the DRM device; KDE runs behind it invisibly. Always run `cachyos-plymouth-fix.sh` after boot. `systemctl --failed` will show `plymouth-quit.service`.

- **Touch → click:** `cachyos-vm-start.sh` sets `GDK_BACKEND=x11 GDK_CORE_DEVICE_EVENTS=1`. Same as Bazzite.

- **Invisible cursor:** Fixed once, persistent. `KWIN_FORCE_SW_CURSOR=1` in `~/.config/plasma-workspace/env/kwin-sw-cursor.sh` inside the VM disk.

- **Display manager:** CachyOS uses `plasmalogin` (not SDDM). Autologin as `deck` into Wayland. `kwin_wayland` starts as child of `startplasma-wayland`.

- **Device name on kernel 7.1.8-1-cachyos-deckify:** hid-steam reports the controller as `"Valve Software Steam Controller"` — config file must match exactly.

- **`qdbus` not installed:** Qt 6-only; use `qdbus6`. The installer creates `~/.local/bin/qdbus → qdbus6` automatically.

- **Monitor socket after VM restart:** Kill old QEMU process before deleting sockets, otherwise FD/inode mismatch → "Connection refused". `cachyos-vm-start.sh` does this automatically.

---

## Controller routing tray (host-side)

`controller-route.py` is a GTK3 system tray app that discovers all running QEMU VMs via their monitor sockets and lets you route the Steam Controller between host and any VM with one click.

```bash
python3 testing/controller-route.py &
```

Requires `python-gobject` and `libayatana-appindicator` (gtk3) on the host, or falls back to `Gtk.StatusIcon`.

---

## SSH quick reference

```bash
# Bazzite
SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never ssh -i ~/.ssh/vm_key \
  -o StrictHostKeyChecking=no -o PasswordAuthentication=no \
  -o BatchMode=yes -p 2222 liveuser@localhost

# CachyOS
SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never ssh -i ~/.ssh/vm_key \
  -o StrictHostKeyChecking=no -o PasswordAuthentication=no \
  -o BatchMode=yes -p 2224 deck@localhost
```

(`SSH_ASKPASS=""` + `SSH_ASKPASS_REQUIRE=never` suppress the KDE ksshaskpass dialog.)
