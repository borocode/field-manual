# NVENC Hardware Encoding Architecture & Session Starvation

## Problem
During continuous multi-day live streaming operations (exceeding 90+ hours of continuous uptime), broadcast applications can encounter abrupt encoder failure:

```text
NVENC Error: OpenEncodeSessionEx failed: out of memory (NV_ENC_ERR_OUT_OF_MEMORY)
```

In the NVIDIA Video Codec API, exceeding the driver's concurrent session limit surfaces as `NV_ENC_ERR_OUT_OF_MEMORY`. Once this limit is reached, all subsequent recording, replay buffering, and stream outputs fail immediately, even when total GPU VRAM and 3D graphics compute utilization remain well below 40%.

## Environment
* **Hardware:** NVIDIA GeForce RTX 3080 Ti (Ampere GA102 architecture).
* **Driver Architecture:** NVIDIA Game Ready / Studio Drivers (64-bit Windows).
* **Software:** OBS Studio 64-bit, Twitch Enhanced Broadcasting client, FFmpeg NVENC pipelines.

## What Was Observed

### 1. Artificial Driver Concurrency Limits
NVIDIA consumer GPUs contain dedicated silicon blocks (NVENC) for video encoding separate from the CUDA graphics cores. On consumer GeForce hardware, the driver enforces an artificial concurrency threshold:
* Historically capped at 3 simultaneous sessions; increased to 5 in 2023, 8 in early 2024, and up to **12 concurrent sessions** in the newest desktop drivers and Video Codec SDKs.
* Enterprise Quadro / RTX Professional cards impose no artificial session limits.

### 2. Multi-Track Transcoding Amplification
Features such as **Twitch Enhanced Broadcasting** shift video transcoding workloads from ingestion servers directly onto the local host. Instead of streaming a single high-bitrate stream, the broadcaster's GPU simultaneously encodes **2 to 5 distinct video tracks** (typically 1440p, 1080p, 720p, 480p, and 360p) across H.264 and HEVC.

On an 8-session limit driver, starting a 5-track broadcast immediately consumes over 60% of the hardware encoder capacity.

### 3. Handle Leakage Over Network Reconnects
During extended multi-day sessions, transient network disruptions trigger automatic stream renegotiation. In long-running processes, socket reconnect logic can allocate replacement encoder instances before the underlying DirectX / CUDA encoder context has fully torn down the previous instances:

```text
# Illustrative diagnostic trace: zombie handle accumulation across repeated reconnects
Session ID    Process    Codec    Resolution    FPS
---------------------------------------------------
66, 80, 85    obs64      H.265    2560x1440     0 (hung)
67, 81, 86    obs64      H.264    1920x1080     0 (hung)
68, 82        obs64      H.264    1280x720      0 (hung)
69, 83        obs64      H.264    852x480       0 (hung)
70, 84        obs64      H.264    640x360       0 (hung)
Total Active Sessions: 12 (Exceeds hardware cap of 8)
```

Twelve zombie handles accumulated in driver state, completely starving the hardware encoder pool.

## What Helped

### 1. Live Forensic Diagnostics
Instead of rebooting the entire operating system, active hardware sessions can be queried in real time:

```powershell
# 1. Query aggregate GPU encoder load and active session count
nvidia-smi --query-gpu=name,encoder.stats.sessionCount,encoder.stats.averageFps,encoder.stats.averageLatency --format=csv

# 2. Inspect individual process handles, codecs, and resolutions
nvidia-smi encodersessions
```

### 2. Operational Workstation Tuning
* **Single-Track Direct Encoding:** For mission-critical marathon broadcasts, disable client-side multi-track transcoding in OBS (`Settings -> Stream -> Enable Enhanced Broadcasting: OFF`). A single 1080p60 NVENC pipeline consumes exactly **1 hardware session**, leaving 7 idle slots to absorb background captures and replays.
* **Process-Level Session Purge:** Terminating the broadcasting parent process immediately causes the NVIDIA kernel driver to release all allocated context handles, returning the active session count to 0 without requiring an OS restart.

## Limits
* **Driver Enforcement:** Hardware session limits are enforced inside the proprietary NVIDIA kernel driver module (`nvlddmkm.sys`).
* **Third-Party Driver Patching:** While community binary patches exist to unlock unrestricted sessions on GeForce cards, they require repatching upon every driver update and can cause driver stability regressions during major OS updates.

## Related Field Notes
* [Single-GPU Dynamic VFIO Passthrough: Hardware Topology & Driver Rebinding](single-gpu-vfio-passthrough-architecture.md) — NVIDIA GPU kernel module lifecycle and hardware isolation.
* [OBS Studio: Cutting Inactive Browser & Media Source Overhead](obs-inactive-browser-and-media-sources.md) — Auditing and idling non-encoding OBS source overhead.
* [OBS Open-Mic Acoustic Audio Alignment via FFT Cross-Correlation](obs-acoustic-audio-alignment.md) — Sub-millisecond audio alignment in OBS broadcast production.
* [Real-Time WebGL Biometric Stream Overlays & Socket Recovery](webgl-hyperate-adrenaline-overlay.md) — WebGL canvas rendering and live GPU compositing load.
* [PowerShell: Why `.ProcessorAffinity` Fails on Bit 31 (`0x80000000`)](powershell-processor-affinity-sign-extension.md) — Process pinning and CPU affinity management for high-load broadcast workloads.

## Sources & Credit
* [NVIDIA Video Codec SDK Documentation](https://developer.nvidia.com/video-codec-sdk) (`NV_ENC_ERR_OUT_OF_MEMORY` error handling).
* [OBS Studio Project source code](https://github.com/obsproject/obs-studio) (FFmpeg NVENC output plugin).
