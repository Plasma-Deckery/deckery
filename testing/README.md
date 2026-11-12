# Testing

`acceptance.py` checks a running Deckery against the behaviour it promises. The
rest of this directory is about QEMU virtual machines with live Steam Controller
passthrough.

---

## Acceptance run

```bash
python3 testing/acceptance.py
```

Unit tests cover the pieces; this covers the seams. It sends real IPC commands
over the control socket, writes real files into `~/.config/deckery`, and reads
the state file the tray actually consumes — so it exercises round trips no unit
test can: a command going out, the daemon rewriting `preferences.toml`, and the
result coming back through `state.json`.

What it checks:

| | |
|---|---|
| Modifiers survive a module of the user's own | a one-line file in `~/.config/deckery` must not silence every combo the base config declares |
| A broken override falls back | a user file that does not parse leaves the shipped config of that name in effect, with a warning naming the file |
| Unknown keys are refused | a misspelt key in `[module]` or a misspelt section name is an error, while button names stay free-form |
| A group switches off and remembers | disabling a whole exclusive group keeps the member choice, so switching it back on returns there |
| The base config cannot be switched off | over the socket either, not just in the tray — and memory does not run away |
| The state file comes back | recreated after being swept out of `/tmp`, without waiting for the state to change |
| A malformed state file does not blank the tray | `/tmp` is mode 1777, so one field of the wrong shape must not cost the whole menu |

Run it on the machine Deckery runs on — the host after a local install, or
inside a test VM after deploying there. Exit code 0 when everything passes.

It borrows the live configuration for the length of the run: `preferences.toml`
and any config file whose name it needs are backed up first and restored on the
way out, including on Ctrl-C. It refuses to start unless makima reports
`lifecycle: ready`, so a failure means a real failure rather than "nothing was
listening".

---

## VM testing

Scripts for testing Deckery in QEMU virtual machines with live Steam Controller passthrough.

Three VMs are supported:

| VM | Distro | SSH port | User | Start script |
|----|--------|----------|------|--------------|
| Bazzite 44 | Fedora/Bazzite (rpm-ostree) | `localhost:2222` | `liveuser` | `vm-start.sh` |
| CachyOS Handheld | Arch/CachyOS (source install) | `localhost:2224` | `deck` | `cachyos-vm-start.sh` |
| Pizzarchy | Arch/Omarchy (Hyprland), emulated Steam Deck OLED | `localhost:2226` | set during install | `pizzarchy-vm-start.sh` |

Every start script also starts the [controller routing tray](#controller-routing-tray-host-side) if it is not already running.

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

- **RAM returned to the host:** `vm-start.sh`, `cachyos-vm-start.sh` and the Pizzarchy scripts add `-device virtio-balloon-pci,free-page-reporting=on`, so the guest reports freed pages and QEMU's RSS shrinks again. The guest kernel only reports free blocks of `page_reporting_order` (default 9 = 2 MiB), which fragmentation limits; `echo 4 | sudo tee /sys/module/page_reporting/parameters/page_reporting_order` in the guest returns noticeably more (measured: ~2.9 GB → ~2.3 GB RSS). Check with `info balloon` on the monitor.

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

- **Monitor socket after VM restart:** Kill old QEMU process before deleting sockets, otherwise FD/inode mismatch → "Connection refused". `cachyos-vm-start.sh` does this automatically — only for the QEMU that owns `cachyos-test/monitor.sock`, other VMs keep running.

---

## Pizzarchy VM

Omarchy (Arch + Hyprland) as packaged by Pizzarchy for the Steam Deck OLED — a non-KDE desktop to test against.

**VM disk:** `~/VMs/pizzarchy-test/install-disk.qcow2` (64 GB, attached as emulated NVMe)  
**UEFI vars:** `~/VMs/pizzarchy-test/OVMF_VARS.fd`  
**Serial log:** `~/VMs/pizzarchy-test/serial.log` (survives the QEMU process)  
**SSH:** `localhost:2226` forwarded to guest port 22 (needs `sshd` enabled in the guest), user chosen in the installer, key `~/.ssh/vm_key` once copied in  
**Installer ISO:** `pizzarchy-omarchy-4.0.4-2026-09-20-x86_64.iso` (stable v2026.09.20) from `/run/media/$USER/Ventoy/Boot ISOs/`; override with `PIZZARCHY_ISO=/path/to.iso`

### Scripts

| Script | What it does |
|--------|-------------|
| `pizzarchy-install-start.sh` | First boot: create a blank disk and boot the installer ISO |
| `pizzarchy-vm-start.sh` | Every later boot, from the installed disk (no ISO) |
| `pizzarchy-controller-attach.sh` | Pass Steam Controller host → Pizzarchy VM |
| `pizzarchy-controller-detach.sh` | Return Steam Controller Pizzarchy VM → host |

### Installing

```bash
# 1. Boot the installer (creates install-disk.qcow2 + fresh UEFI vars)
bash testing/pizzarchy-install-start.sh

# 2. The installer is controller-only: route the controller in once the
#    QEMU window is up (or pick "Pizzarchy-Install" in the tray)
bash testing/pizzarchy-controller-attach.sh

# 3. Install onto the only disk offered, then power off the VM.
#    The installer downloads Steam during setup — QEMU's user-mode NAT
#    provides the internet access, nothing to configure.
```

`pizzarchy-install-start.sh` refuses to run if `install-disk.qcow2` already exists, so an installed VM can't be wiped by accident. To really reinstall from scratch: `PIZZARCHY_FORCE_REINSTALL=yes bash testing/pizzarchy-install-start.sh` (wipes the disk and the UEFI NVRAM).

### Typical test session

```bash
# 1. Start VM
bash testing/pizzarchy-vm-start.sh

# 2. Pass controller to VM
bash testing/pizzarchy-controller-attach.sh

# 3. Return controller to host when done
bash testing/pizzarchy-controller-detach.sh
```

### Known quirks — Pizzarchy VM

- **NVMe, not virtio:** the installer only accepts `/dev/nvme0n1` or `/dev/mmcblk0` as a target. A virtio disk shows up as `/dev/vda` and is refused with "no eligible install disk".

- **SMBIOS spoofed as Steam Deck OLED:** both scripts pass `-smbios type=1,manufacturer=Valve,product=Galileo` (and type 2). The installer's wipe gate checks `product_name == Galileo` and a `Valve` vendor before it touches any disk; without this, picking the disk bounces back to "no eligible install disk". Pizzarchy's own QEMU test harness does the same — there is no bypass.

- **Stable release, not Fast-Install:** the Fast-Install prerelease aborts every interactive install with "cidata drive carries no 'preinstalls' file". The stable v2026.09.20 ISO does not have that check.

- **No zoom-to-fit:** unlike the other VMs, `-display gtk` runs without `zoom-to-fit=on` — with it the display went permanently blank after a window resize during the install.

- **Small footprint:** `-smp 2 -m 4G`, because the host is the Steam Deck itself.

- **One QEMU at a time per VM:** both scripts kill only the QEMU that owns `pizzarchy-test/monitor.sock` before starting. The install script does so only after its disk check, so a refused run leaves a running VM alone.

---

## Controller routing tray (host-side)

`controller-route.py` is a GTK3 system tray app that routes the Steam Deck controller (USB `28de:1205`) between the host and any running QEMU VM with one click.

Every three seconds it lists the running `qemu-system` processes, takes each one's `-monitor unix:` socket and `-name`, and asks each monitor (`info usb`) which VM currently holds the controller. The menu shows "Host" plus one entry per VM, with a check mark on the current owner. Picking an entry detaches the controller from the VM that has it and `device_add`s it into the new one — the same `usb-host,bus=xhci.0,…,id=steamctrl` command the `*-controller-attach.sh` scripts send, so the tray and the scripts can be mixed freely. VMs without a monitor socket (such as unrelated QEMU instances) are not listed.

You normally don't start it by hand: `vm-start.sh`, `cachyos-vm-start.sh`, `pizzarchy-vm-start.sh` and `pizzarchy-install-start.sh` all call `ensure-controller-tray.sh`, which starts the tray in the background (log: `/tmp/controller-route.log`) unless one is already running. To start it manually:

```bash
python3 testing/controller-route.py &
```

Requires `python-gobject` and `libayatana-appindicator` (gtk3 variant) on the host; without the latter it falls back to `Gtk.StatusIcon`. Also needs `lsusb` and `pgrep`.

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

# Pizzarchy (user chosen in the installer)
SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never ssh -i ~/.ssh/vm_key \
  -o StrictHostKeyChecking=no -o PasswordAuthentication=no \
  -o BatchMode=yes -p 2226 <user>@localhost
```

(`SSH_ASKPASS=""` + `SSH_ASKPASS_REQUIRE=never` suppress the KDE ksshaskpass dialog.)
