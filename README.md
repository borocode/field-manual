# Field Manual

A collection of technical field notes drawn from real debugging, systems administration, and software engineering sessions.

Each note documents a specific problem where the root cause or working fix was non-obvious, written so that:
1. **Humans** can quickly see what failed, what was measured, what helped, and where the caveats are.
2. **Coding agents** can use the notes as structured reference material when troubleshooting similar symptoms.

> **Scope & Safety Notice:** These notes record observations from specific machines and project setups. They are reference material, not universal rules, and should never override your own security policies, backups, or verification steps. Unconfirmed hypotheses or single-machine workarounds are explicitly labeled.

---

## Note Format

Every note in `notes/` follows a six-part structure:

1. **The Problem** — What we were trying to do and the failure or symptom we hit.
2. **Environment** — Relevant OS, runtime, hardware, and software versions.
3. **What Was Observed** — Exact errors, measurements, and disproven hypotheses.
4. **What Helped** — Reproducible steps, commands, and rollback instructions.
5. **Limits** — What was only tested on one machine, side effects, and edge cases.
6. **Sources & Credit** — Upstream documentation, tools, and license details.

---

## Index of Notes

### Hardware & Reverse Engineering
* [**Android Termux: Native ARM64 Toolchains, Thermal Limits & Wakelocks**](notes/android-termux-arm64-toolchain-and-wakelocks.md)  
  Compiling C/C++ runtimes directly on Android without root, managing OS Doze mode freezes via `termux-wake-lock`, and thread partitioning across heterogeneous big.LITTLE core clusters to prevent thermal throttling.
* [**iPod Nano 3G (A1236) Reverse Engineering & Silicon Bringup**](notes/a1236-ipod-nano-3g-reverse-engineering.md)  
  Samsung `S5L8702` silicon self-identification vs marketed `S5L8701`, SecureROM DFU exploit via `wInd3x`, the 256 KB DFU transfer buffer boundary, and mapping FMC NAND registers for physical hardware execution.
* [**Rabbit R1 Hardware Architecture, Bootloader Unlock & GSI Porting**](notes/rabbit-r1-bootloader-unlock-and-gsi.md)  
  Bypassing vendor cloud tokens via MediaTek MT6765 BROM exploit (`mtkclient`), disabling AVB 2.0 (`dm-verity`), flashing Project Treble ARM64 A/B GSIs, and driving the 360° motorized camera via GPIO daemon.
* [**Provenance & Postmortems: Defunct, Halted, and Superseded Tools**](notes/defunct-protocols-and-homebrew-provenance.md)  
  Historical lineage across console homebrew (Switch CFW `MOD0` `LNY2` TLS breaks and memory pool exhaustion), P2P media dead tracker backoffs, August 2026 swap halts, and empirical bonding-curve sniper audits.

### Broadcast, GPU & Acoustic Engineering
* [**NVENC Hardware Encoding Architecture & Session Starvation**](notes/nvenc-hardware-encoding-architecture.md)  
  Diagnosing driver session exhaustion (`NV_ENC_ERR_OUT_OF_MEMORY`), Twitch Enhanced Broadcasting multi-track GPU allocation, zombie encoder handle leaks during socket renegotiation, and `nvidia-smi encodersessions` forensics.
* [**OBS Open-Mic Acoustic Audio Alignment via FFT Cross-Correlation**](notes/obs-acoustic-audio-alignment.md)  
  Sub-millisecond desktop/mic alignment (+8 ms Desktop / 0 ms Mic) using audio chirp testing, resolving live timestamp discontinuities via FFmpeg `aresample` PTS reconstruction, and eliminating speaker bleed without aggressive noise gates.
* [**OBS Studio: Inactive Browser & Media Source Overhead via `obs-websocket`**](notes/obs-inactive-browser-and-media-sources.md)  
  Auditing and toggling `shutdown` (browser) and `close_when_inactive` (media) across large scene collections over WebSocket v5, dropping memory by over 2 GB without breaking alert or WebRTC streams.
* [**Real-Time WebGL Biometric Stream Overlays & Socket Recovery**](notes/webgl-hyperate-adrenaline-overlay.md)  
  Handling silent WebSocket telemetry deadlocks when keep-alive heartbeats continue but metrics freeze, 90-second watchdog resets, and scene group alpha compensation.

### Systems, Networks & Infrastructure
* [**Single-GPU Dynamic VFIO Passthrough: Hardware Topology & Driver Rebinding**](notes/single-gpu-vfio-passthrough-architecture.md)  
  Architectural breakdown of dynamic single-GPU passthrough on Linux (AMD Ryzen 9 5950X / NVIDIA RTX 3080 Ti): display manager teardown, driver unbinding/rebinding hooks, dual-CCD CCX cache latency isolation, and raw NVMe VirtIO boot without dual-booting.
* [**Headless 24/7 Unattended Disk Unlock (LUKS2 + TPM 2.0)**](notes/headless-unattended-disk-unlock-tpm2.md)  
  Configuring `systemd-cryptenroll` with Limine UKI on NVMe root, configuring PCR 7 Secure Boot and signed UKI policy while avoiding raw PCR 4/9 kernel upgrade lockout traps, and verifying passphrase validation non-destructively in userland.
* [**Cross-Play Minecraft Architecture: Geyser, Bedrock UDP & Reverse Tunneling**](notes/minecraft-crossplay-geyser-tunneling.md)  
  Bridging Java TCP and Bedrock UDP (RakNet/NetherNet) via PaperMC, Geyser, and Floodgate in Docker; reverse TCP tunneling with DNS SRV records; and local LAN discovery on consoles without Xbox Live auth.
* [**Lightning Network Peer Discovery & Gossip Storm Prevention**](notes/lightning-network-peer-gossip-management.md)  
  Preventing BoltDB memory churn and OOM crashes on SBCs (Raspberry Pi) via staggered rate-limited peering (2.5s pacing) and multi-mirror Mempool explorer failover.
* [**PowerShell: Why `.ProcessorAffinity` Fails on Bit 31 (`0x80000000`)**](notes/powershell-processor-affinity-sign-extension.md)  
  Resolving `SetValueInvocationException: "The parameter is incorrect"` in 64-bit PowerShell when setting affinity masks above `0x7FFFFFFF`, explaining `Int32` sign-extension bugs, and providing the `0xC0000000L` fix.

### Autonomous Agent Workflows
* [**Autonomous Agent Monetization: Whop MCP vs. L402 Lightning Tollbooths**](notes/agent-monetization-whop-mcp-vs-l402-tollbooths.md)  
  Comparing agent-first Web2 platforms (Whop MCP, two-phase commit tokens, raw `.md` mirrors) against crypto-native M2M micropayments (L402 Lightning tollbooths); real-world liquidity findings from 600+ payment challenges; and data rights/ToS invariants.
* [**Multi-Agent Relay Architecture: The Cloud Architect to Local Compiler Pattern**](notes/multi-agent-relay-architecture.md)  
  Eliminating hallucinated pull requests by pairing cloud API authoring with local host compiler verification (`cargo check` / `cargo test` borrow-checker catches), backed by the invariant of "disk truth over model confidence."
* [**Agentic Engineering: Managing Long-Running Binary Porting Projects**](notes/agent-handoff-and-artifact-gating.md)  
  State-management patterns from multi-week recompilation projects: SHA-256 build manifests, embedded runtime markers, and capping diagnostic logs to prevent rebuild thrashing loops.

---

## Pre-Publication Review Checklist

Automated pattern scanning (`python scripts/check_sensitive_patterns.py`) is included **only as a secondary lint check**. Before pushing any commit to a public remote, perform a manual review of:
1. **Filenames and directory structure** (`git status --ignored`, `git ls-files`)
2. **Full text of every note** (checking for prose that identifies private infrastructure, account names, or third-party confidential data)
3. **Git commit metadata and history** (`git log --stat -p`, `git log --format="%an <%ae>"`)
