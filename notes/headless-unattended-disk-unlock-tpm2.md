# Headless 24/7 Unattended Disk Unlock (LUKS2 + TPM 2.0)

## Problem
Running 24/7 headless servers, broadcast workstations, or remote compute nodes with Full Disk Encryption (LUKS2) presents a critical operational challenge: any power interruption, watchdog crash, or automated kernel upgrade leaves the machine halted at an early boot password prompt, requiring manual physical access or out-of-band IP-KVM intervention to enter the disk decryption passphrase.

## Environment
* **Operating System:** Linux (Arch / systemd-based distributions).
* **Storage Architecture:** NVMe root volume formatted as LUKS2 (`/dev/nvme0n1p2`).
* **Hardware Security:** TPM 2.0 Resource Manager (`/dev/tpmrm0`, `tpm_crb_acpi` or `tpm_tis`).
* **Boot Architecture:** Limine bootloader or systemd-boot executing a Unified Kernel Image (UKI with systemd-stub).

## What Was Observed

### 1. The PCR Policy Tradeoff
Binding the TPM disk unlock key to Platform Configuration Registers (PCRs) requires balancing security against boot reliability:
* **The "Zero Security" Trap:** Binding exclusively to **PCR 7** (Secure Boot state) on systems where Secure Boot is disabled provides zero tamper protection; any external boot drive or modified kernel will still release the disk key.
* **The "Fragile Boot" Trap:** Binding directly to raw kernel or initramfs measurement hashes (**PCR 4** or **PCR 9**) without a cryptographic signature policy causes subsequent kernel updates (`pacman -S linux` or `apt upgrade`) to alter the measured register values. Upon mismatch, the TPM refuses to release the key, halting unattended reboots and falling back to an early-boot interactive passphrase prompt.

```text
Kernel Update Applied ──> UKI Hash Changes ──> PCR 4/9 Measurement Mismatch ──> TPM Refuses Key ──> Boot Halted
```

### 2. Initramfs Hook Incompatibilities
Modern distributions often use custom `mkinitcpio` or `dracut` drop-in configurations. Replacing the legacy busybox `encrypt` hook with `systemd` / `sd-encrypt` can break custom late hooks (such as `btrfs-overlayfs` or ZFS snapshot rollbacks) that expect shell scripts rather than systemd device-mapper targets.

## What Helped

### 1. Mandatory Pre-Flight LUKS Header Backup
Before enrolling any hardware security tokens into LUKS2 keyslots, dump the metadata header and keyslots to a protected backup image on external/offline storage (or a separate administrative partition):

```bash
# Backup 16 MB LUKS2 header to an administrative backup directory or external drive
sudo cryptsetup luksHeaderBackup /dev/nvme0n1p2 \
  --header-backup-file /mnt/secure-backup/luks-header-pre-tpm.img

# Ensure strict root-only permissions
sudo chmod 0400 /mnt/secure-backup/luks-header-pre-tpm.img
```

### 2. Passphrase Verification Across Active Keyslots
Never attempt TPM key enrollment based on assumptions about passwords or slots. First inspect all active keyslots, then test your human recovery passphrase non-destructively:

```bash
# 1. Inspect active keyslot assignments (e.g. slot 0 for password)
sudo cryptsetup luksDump /dev/nvme0n1p2

# 2. Test the human passphrase non-destructively; verbose output (-v) reports which keyslot unlocked
sudo cryptsetup open --test-passphrase -v /dev/nvme0n1p2
```

If this command exits with status 0, the human recovery passphrase is confirmed valid before modifying boot configuration.

### 3. Balanced TPM2 Policy Architecture via `systemd-cryptenroll`
To achieve reliable unattended reboot across kernel updates while protecting against physical drive theft:
* **Recommended Architecture (Secure Boot + Signed UKI):** Measure **PCR 7** (Secure Boot state) paired with a signed **PCR 11** policy (`systemd-measure`). This allows new kernel updates signed with your private build key to boot unattended without recalculating raw hash registers:
  ```bash
  # Enroll TPM 2.0 token with PCR 7 and signed UKI public key
  sudo systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=7 \
    --tpm2-public-key=/etc/systemd/tpm2-pcr-public-key.pem /dev/nvme0n1p2
  ```
* **Firmware-Only Baseline (Without UKI signing):** If UKI signature infrastructure is not in place, bind to **PCR 0+2+7**:
  ```bash
  sudo systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=0+2+7 /dev/nvme0n1p2
  ```
* **Avoid Raw PCR 4/9:** Never bind to literal PCR 4 or PCR 9 hashes without `systemd-measure` signatures, as standard package updates will alter the measurements and require manual passphrase entry.

### 4. Preserving the Human Recovery Slot
`systemd-cryptenroll` places the sealed hardware secret into an independent keyslot (e.g. Keyslot 1 or 2). **Never delete the primary human passphrase keyslot.** If motherboard firmware is upgraded or BIOS settings are cleared, having the passphrase keyslot intact allows the operator to unlock manually and re-enroll the TPM.

### 5. `crypttab` Configuration
Update `/etc/crypttab` (or `/etc/crypttab.initramfs` on Arch Linux systems utilizing the `sd-encrypt` initramfs hook) to instruct `systemd-cryptsetup` in the initramfs to attempt TPM unsealing automatically:

```text
# <target name>  <source device>                             <key file>  <options>
root             UUID=12345678-1234-1234-1234-123456789abc   none        tpm2-device=auto,discard
```

## Limits
* **Bus Sniffing & Physical Interception:** Standard TPM2 unsealing transmits the decrypted volume key across the motherboard SPI/LPC bus during early boot. Without TPM bus encryption (supported in systemd 255+ with signed credentials), dedicated hardware attackers with logic analyzers can theoretically intercept the key during unseal.
* **Firmware Flashes:** Flashing motherboard UEFI/BIOS firmware alters PCR 0, requiring a human operator to enter the manual recovery password once after the update to re-enroll the TPM.

## Related Field Notes
* [Single-GPU Dynamic VFIO Passthrough](single-gpu-vfio-passthrough-architecture.md) — Host kernel hooks, Limine UKI configuration, and hardware isolation.
* [Cross-Play Minecraft Architecture: Geyser & Reverse Tunneling](minecraft-crossplay-geyser-tunneling.md) — 24/7 headless container orchestration.
* [Android Termux: Native ARM64 Toolchains, Thermal Limits & Wakelocks](android-termux-arm64-toolchain-and-wakelocks.md) — Long-running background daemon persistence.

## Sources & Credit
* [Arch Linux systemd-cryptenroll Documentation](https://man.archlinux.org/man/systemd-cryptenroll.1.en).
* [TCG TPM 2.0 PC Client Platform Firmware Profile Specification](https://trustedcomputinggroup.org/resource/pc-client-specific-platform-firmware-profile-specification/).
* [Limine Bootloader Documentation](https://limine-bootloader.org/).
