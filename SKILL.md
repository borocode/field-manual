---
name: field-manual
description: Reference collection of empirical debugging field notes covering hardware reverse-engineering, GPU broadcast pipelines, systems administration, Linux/Windows virtualization, and autonomous multi-agent engineering workflows.
---

# Field Manual — Agent Navigation Guide

Use this repository as **reference material** when investigating matching technical symptoms.

## Usage Guidelines for Agents
1. **Reference, Not Dogma:** Each note describes what was observed and tested in a specific environment, along with an explicit `## Limits` section. Always verify current system state before applying a command or configuration change.
2. **Preserve Rollback Paths:** When applying settings described in these notes (such as driver unbinding, process affinity masks, or source modifications), record the prior state first so the user can revert cleanly.
3. **Disk Truth Over Model Confidence:** Do not assume a patch compiles or a service runs without captured terminal output.

## Available Notes by Domain

### Hardware & Reverse Engineering
- [`notes/android-termux-arm64-toolchain-and-wakelocks.md`](notes/android-termux-arm64-toolchain-and-wakelocks.md): Native ARM64 toolchains, OS Doze prevention via `termux-wake-lock`, and big.LITTLE thermal core budgeting.
- [`notes/a1236-ipod-nano-3g-reverse-engineering.md`](notes/a1236-ipod-nano-3g-reverse-engineering.md): Samsung S5L8702 silicon identification, 256 KB DFU transfer boundaries, and FMC NAND registers.
- [`notes/rabbit-r1-bootloader-unlock-and-gsi.md`](notes/rabbit-r1-bootloader-unlock-and-gsi.md): MediaTek MT6765 BROM exploit via `mtkclient`, disabling AVB, and Project Treble ARM64 A/B GSI flashing.
- [`notes/defunct-protocols-and-homebrew-provenance.md`](notes/defunct-protocols-and-homebrew-provenance.md): Historical provenance on Switch CFW (`MOD0` TLS breaks), dead P2P tracker backoffs, and cross-chain bridge halts.

### Broadcast, GPU & Acoustic Engineering
- [`notes/nvenc-hardware-encoding-architecture.md`](notes/nvenc-hardware-encoding-architecture.md): NVIDIA driver session limits, multi-track GPU allocation, zombie socket handle leaks, and `nvidia-smi encodersessions` forensics.
- [`notes/obs-acoustic-audio-alignment.md`](notes/obs-acoustic-audio-alignment.md): Sub-millisecond desktop/mic alignment using audio chirps and FFmpeg `aresample` PTS timeline reconstruction.
- [`notes/obs-inactive-browser-and-media-sources.md`](notes/obs-inactive-browser-and-media-sources.md): Toggling `shutdown` and `close_when_inactive` over `obs-websocket` v5 to reduce idle memory by gigabytes.
- [`notes/webgl-hyperate-adrenaline-overlay.md`](notes/webgl-hyperate-adrenaline-overlay.md): 90-second dead-socket recovery watchdogs for silent telemetry freezes and OBS scene group alpha compensation.

### Systems, Networks & Infrastructure
- [`notes/single-gpu-vfio-passthrough-architecture.md`](notes/single-gpu-vfio-passthrough-architecture.md): Dynamic single-GPU passthrough on Linux (Ryzen CCX cache isolation, driver unbind/rebind hooks, and raw NVMe VirtIO boot).
- [`notes/headless-unattended-disk-unlock-tpm2.md`](notes/headless-unattended-disk-unlock-tpm2.md): LUKS2 + TPM 2.0 systemd-cryptenroll integration with Limine UKI, configuring PCR 7 Secure Boot and signed UKI policy while avoiding raw PCR 4/9 update lockout traps.
- [`notes/minecraft-crossplay-geyser-tunneling.md`](notes/minecraft-crossplay-geyser-tunneling.md): Bridging Java TCP and Bedrock UDP via PaperMC, Geyser, and Floodgate with reverse TCP tunnels and DNS SRV records.
- [`notes/lightning-network-peer-gossip-management.md`](notes/lightning-network-peer-gossip-management.md): Mitigating BoltDB freelist page churn and OOM crashes on SBCs via staggered peering (2.5s pacing).
- [`notes/powershell-processor-affinity-sign-extension.md`](notes/powershell-processor-affinity-sign-extension.md): Resolving `ERROR_INVALID_PARAMETER` in 64-bit PowerShell when setting affinity masks with bit 31 set via `[IntPtr]0xC0000000L`.

### Autonomous Agent Workflows
- [`notes/agent-monetization-whop-mcp-vs-l402-tollbooths.md`](notes/agent-monetization-whop-mcp-vs-l402-tollbooths.md): Whop MCP two-phase commits vs. L402 Lightning tollbooth micropayments; real-world buyer liquidity findings and ToS invariants.
- [`notes/multi-agent-relay-architecture.md`](notes/multi-agent-relay-architecture.md): Pairing cloud API authoring with local compiler verification (`cargo check` / `cargo test` borrow-checker catches).
- [`notes/agent-handoff-and-artifact-gating.md`](notes/agent-handoff-and-artifact-gating.md): Structuring `HANDOFF.md`, `BUILD_MANIFEST.md`, runtime build tags, and log caps to prevent thrashing loops.
