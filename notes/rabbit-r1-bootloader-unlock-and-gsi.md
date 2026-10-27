# Rabbit R1 Hardware Architecture, Bootloader Unlock & GSI Porting

> **Warning:** Unlocking the bootloader irrevocably wipes all user data and carries a risk of permanently bricking the device if the preloader, partition table, or BROM state is corrupted. Always create and verify a complete physical flash dump via BROM mode before attempting any modifications.

## Problem
The Rabbit R1 is a dedicated AI handheld device designed to run a single proprietary launcher (`com.rabbit.r1.launcher`) on top of an Android 13 AOSP base. Users seeking to run standard Android, postmarketOS, or hardened custom ROMs encounter:
1. No official bootloader unlock tokens or manufacturer developer portals.
2. Android Verified Boot (AVB 2.0 / `dm-verity`) preventing modifications to system partitions.
3. Proprietary hardware controls for the 360° motorized rotating camera lens and scroll wheel.

## Environment
* **Hardware:** Rabbit R1 Handheld.
* **SoC:** MediaTek Helio P35 (`MT6765`) — 8-core ARM Cortex-A53.
* **Memory & Storage:** 4 GB LPDDR4X, 128 GB eMMC 5.1.
* **Display:** 2.88-inch TFT touchscreen (240x282 resolution).
* **Base Architecture:** Project Treble ARM64 A/B (system-as-root), dynamic `super` partition.
* **Host Toolchain:** Linux / macOS / Windows with Python 3, `mtkclient`, and Android platform-tools (`fastboot`, `adb`).

## What Was Observed

### 1. BROM Exploit Vulnerability
Because the device runs on the MediaTek MT6765 chipset, its BootROM is vulnerable to the standard SLA/DA handshake bypass in `mtkclient`. Physical access to the hardware enables full BootROM access without requiring software authorization or developer credentials:

* Holding the **Push-To-Talk (PTT)** button while plugging the USB-C cable into a host PC forces the SoC into MediaTek BROM mode (`0e8d:0003`).

### 2. Verified Boot Enforcement
Stock images strictly enforce cryptographic signature validation via `vbmeta`. Any modification to the `system` or `boot` partitions without disabling AVB results in a boot loop at the initial splash screen (`dm-verity verification failed`).

## What Helped

### 1. Bootloader Unlock via BROM
Using `mtkclient`, the security configuration partition (`seccfg`) can be overwritten directly from BROM mode:

```bash
# 1. Clone mtkclient and install dependencies
git clone https://github.com/bkerler/mtkclient.git
cd mtkclient
pip install -r requirements.txt

# 2. Enter BROM mode (hold PTT button while connecting USB-C)
# 3. Dump full stock firmware backup (CRITICAL recovery fallback)
python mtk.py rl r1_stock_backup/

# 4. Write bootloader unlock flag to seccfg
python mtk.py da seccfg unlock

# 5. Transition to fastboot mode (using mtkbootcmd.py from r1_escape)
python mtkbootcmd.py FASTBOOT

# 6. Disable Android Verified Boot via fastboot flags
fastboot flash --disable-verity --disable-verification vbmeta vbmeta.img
```

### 2. Flashing Treble Generic System Images (GSI)
Because the R1 adheres to Google's Project Treble standard on Android 13, it boots generic ARM64 A/B system images without requiring device-specific kernel recompilation:

```bash
# 1. Transition from bootloader to userspace fastbootd
fastboot reboot fastboot

# 2. Flash target GSI system image to the dynamic partition
fastboot flash system lineage-21.0-arm64-bvN.img

# 3. Wipe userdata to clear cached proprietary launcher states
fastboot -w

# 4. Reboot into the new operating system
fastboot reboot
```

### 3. Peripheral Hardware Adaptation
* **Screen Resolution & DPI:** Set the window manager density to ensure UI elements scale correctly on the 240x282 display:
  ```bash
  adb shell wm density 160
  ```
* **Motorized Camera Lens:** The 360° rotating 8 MP camera is driven by an internal stepper motor. Community tooling (`r1_escape`) provides automated bootloader unlock and Treble GSI flashing scripts; full camera rotation and dynamic angle positioning under generic Android requires vendor camera HAL integration or reverse-engineered motor control daemons.

## Limits
* **Kernel Mainlining:** The MT6765 relies on a downstream MediaTek 4.19 / 5.4 Board Support Package (BSP) kernel with proprietary HAL blobs. Upstream mainline Linux kernel support requires reverse-engineering power management IC (PMIC) and display DSI timings.
* **Pixel-Specific OS Restrictions:** Distributions strictly tied to Google Titan M2 hardware attestation (such as upstream GrapheneOS) cannot run natively on MediaTek silicon; hardened AOSP GSI builds with sandboxed microG and hardened malloc provide the closest functional alternative.

## Related Field Notes
* [Android Termux: Native ARM64 Toolchains, Thermal Limits & Wakelocks](android-termux-arm64-toolchain-and-wakelocks.md) — Running native compute and managing process execution on ARM64 Android runtimes.
* [iPod Nano 3G (A1236) Reverse Engineering & Silicon Bringup](a1236-ipod-nano-3g-reverse-engineering.md) — BootROM exploitation and low-level peripheral mapping.
* [Provenance & Postmortems: Defunct Tools & Protocols](defunct-protocols-and-homebrew-provenance.md) — Bootloader security, legacy console homebrew, and ABI breaks.

## Sources & Credit
* B. Kerler ([mtkclient](https://github.com/bkerler/mtkclient)) for the MediaTek BROM exploit implementation.
* AndyCGYan and the [Phh-Treble community](https://github.com/phhusson/treble_experimentations) for ARM64 GSI development.
* The open-source [RabbitHoleEscapeR1/r1_escape repository](https://github.com/RabbitHoleEscapeR1/r1_escape) for unlock and flash automation scripts.
