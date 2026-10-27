# Android Termux: Native ARM64 Toolchains, Thermal Limits & Wakelocks

## Problem
Running heavy compute workloads, native C/C++ daemons, or continuous background utilities on modern Android devices typically runs into three major barriers:
1. **Root & Cross-Compilation Assumptions:** Standard guides assume the device is rooted or require setting up complex Android NDK cross-compilation environments on a separate Linux/x86 host.
2. **Aggressive OS Deep Sleep (Doze Mode):** Android aggressively suspends background processes. The moment the phone screen locks or the device sits idle on battery, the kernel puts background processes into cgroup freezes, dropping network sockets and pausing worker threads.
3. **Severe Thermal Throttling on Prime Cores:** Modern mobile SoCs (Qualcomm Snapdragon, MediaTek Dimensity, Google Tensor) feature high thermal density. Saturating all 8 cores forces the thermal governor to throttle CPU clock frequencies down to minimum baseline states (~400–600 MHz) within 90 seconds.

## Environment
* **Platform:** Android 11+ (ARM64 / aarch64 architecture).
* **Terminal Environment:** Termux userspace (F-Droid / GitHub releases, not the obsolete Google Play build).
* **Toolchain:** Clang / LLVM, CMake, `libuv`, OpenSSL, and `termux-tools`.

## What Was Observed

### 1. The Screen-Off Process Freeze & Doze Mode
When a native CLI binary (such as an encrypted tunnel or background worker) runs in standard Termux without explicit power configurations, locking the phone triggers two distinct power-saving mechanisms:
1. **Screen-Off Sleep:** The CPU halts execution threads unless a partial wakelock is held.
2. **Android Doze Mode:** Once the device is stationary on battery, Doze mode ignores userland wakelocks and restricts background network access entirely unless battery optimization is set to "Unrestricted".

```text
[Screen Locked / User Idle] ──> Android Power Manager ──> cgroup freeze
                                           │
                        (Wakelock prevents immediate sleep,
                         but Doze kills network unless Unrestricted)
```

### 2. Thermal Runaway on Heterogeneous Core Clusters
Modern mobile chipsets use heterogeneous **big.LITTLE** or **Tricluster** CPU layouts:
* 1x "Prime" Core (e.g. Cortex-X3 / X4)
* 3-4x "Performance" Cores (e.g. Cortex-A715 / A720)
* 3-4x "Efficiency" Cores (e.g. Cortex-A510 / A520)

Running unconstrained multi-threading (allocating all 8 hardware threads) causes the tiny physical surface of the SoC to reach $\ge 70^\circ\text{C}$ in seconds. The Linux kernel governor triggers emergency thermal throttling, degrading overall compute throughput below what 4 cool cores produce continuously.

## What Helped

### 1. Rootless Native Compilation Bootstrap
Rather than cross-compiling on a desktop PC and transferring binaries via ADB, the complete Clang/CMake toolchain can be built directly inside unprivileged Termux userspace:

```bash
# Update and install native ARM64 toolchain
pkg update -y
pkg install -y git cmake clang make libuv openssl termux-tools

# Compile directly on device using available threads
cmake -B build -D CMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

### 2. Preventing Process Suspension: Wakelocks + Unrestricted Battery
To ensure worker threads, sockets, and timers execute continuously with the screen turned off:
1. **Mandatory OS Setting:** In Android system settings (`App Info -> Termux -> Battery`), toggle the battery profile to **"Unrestricted"**. This bypasses Android Doze mode and prevents the system from killing background sockets.
2. **Acquire Partial Wakelock:** Execute `termux-wake-lock` (provided by `termux-tools`) before launching the background process to prevent the CPU from entering deep sleep:
   ```bash
   termux-wake-lock
   ```
3. When the workload completes, release the power lock:
   ```bash
   termux-wake-unlock
   ```

### 3. Thermal Budgeting & Thread Partitioning
Benchmarking on Qualcomm Snapdragon 8-series platforms demonstrated that **thread budgeting beats thread count**:

| Hardware Platform | Total Cores | Recommended Threads | Sustained SoC Temp | Operational Result |
| :--- | :--- | :--- | :--- | :--- |
| **8-Core Mobile SoC (Standard)** | 8 | `4` or `5` threads | $38^\circ\text{C} - 42^\circ\text{C}$ | Stable continuous throughput; zero thermal throttling |
| **8-Core Mobile SoC (Max Effort)**| 8 | `6` threads | $45^\circ\text{C} - 48^\circ\text{C}$ | Moderate warmth; acceptable for short runs |
| **8-Core Mobile SoC (Unbudgeted)**| 8 | `8` threads | $>70^\circ\text{C}$ | Throttled down to minimum frequency in $<2\text{ min}$ |
| **SBC (Raspberry Pi 4 / 5)** | 4 | `4` threads | $45^\circ\text{C} - 52^\circ\text{C}$ | Sustained max throughput (with heatsink/fan) |

Leaving 2–3 efficiency cores free allows Android system daemons, display managers, and network interfaces to operate smoothly without competing with worker threads.

## Limits
* **Non-Root Limitations:** Without root (`su`), users cannot configure hugepages via sysctl (`/proc/sys/vm/nr_hugepages`) or directly write to Model-Specific Registers (MSR). Workloads that depend on hardware prefetcher disabling will operate in software-fallback mode.
* **Android 12+ Phantom Process Killer:** Android 12+ enforces a global, system-wide cap of 32 total background child processes across all applications (threads do not count toward this limit, but separate child process forks spawned by shells, compilers, or background utilities do). Exceeding this global threshold triggers mass SIGKILL terminations by the OS. This limit cannot be toggled from within Termux and must be configured via ADB from a host computer:
  * *Android 12:* Run `adb shell "/system/bin/device_config set_sync_disabled_for_tests persistent"` followed by `adb shell "/system/bin/device_config put activity_manager max_phantom_processes 2147483647"`.
  * *Android 12L / 13+:* Run `adb shell "/system/bin/settings put global settings_enable_monitor_phantom_procs false"`.
* **Vendor Aggressive Killers:** Certain aggressive OEM Android skins (e.g. MIUI / HyperOS, EMUI) terminate background processes after 30+ minutes regardless of wakelocks unless "Auto-start" and "No restrictions" are toggled in manufacturer settings.

## Related Field Notes
* [Rabbit R1 Hardware Architecture, Bootloader Unlock & GSI Porting](rabbit-r1-bootloader-unlock-and-gsi.md) — Unlocking BootROM and managing hardware peripherals on ARM64 handhelds.
* [Headless 24/7 Unattended Disk Unlock (LUKS2 + TPM 2.0)](headless-unattended-disk-unlock-tpm2.md) — Background Linux daemon persistence, boot orchestration, and unattended recovery.

## Sources & Credit
* [Termux Project Repository](https://github.com/termux/termux-app) and the [termux-api package](https://github.com/termux/termux-api).
* [Android Open Source Project (AOSP) Power Management Architecture](https://source.android.com/docs/core/power) (`PARTIAL_WAKE_LOCK`).
