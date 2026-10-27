# Provenance & Postmortems: Defunct, Halted, and Superseded Tools Across Console Homebrew, P2P Media, and On-Chain Rails

## 1. The Problem
When software projects, custom firmware (CFW) ecosystems, P2P relays, or on-chain protocols shut down, pause operations, or break across OS ABI boundaries, documentation usually disappears with them—or worse, old tutorials and hardcoded defaults remain online and quietly break new setups.

Keeping an explicit provenance record of **what broke or halted and what was learned from it** prevents repeating dead routes and preserves technical history.

## 2. Environment
* **Console Homebrew:** Nintendo Switch 1 (`Horizon OS` up to `22.1.0`, `Atmosphère 1.10–1.11.1`, `libnx 4.10+`) and PowerPC-to-AArch64 static binary recompilation toolchains
* **Decentralized Media Clients:** `lnbits/napstr` (Rust/Tauri Nostr + Tor audio seeder) and `Stremio 4.4.181` (`EngineFS` / `torrent-stream` Node.js daemon)
* **On-Chain Bridges & Launchpads:** Bitcoin/Lightning cross-chain swap services (`Boltz`, `Atomiq Labs`) and high-speed Arbitrum Orbit L2 bonding-curve launchpad contracts

## 3. What Was Observed & Provenance Record

### A. Nintendo Switch CFW & Sysmodule Evolution (2018–2026)
Inspecting and modernizing a long-lived Switch V1 SD card on **Horizon OS 22.1.0 / Atmosphère 1.11.1** exposed three distinct generations of obsolete or incompatible software:

1. **Obsolete CFW Loaders & Legacy Toolkits:**
   * Early CFW loaders and distribution packages (e.g., `ReiNX`, `KosmosToolbox`, `KosmosUpdater`) are unmaintained and non-functional on modern Horizon firmware.
2. **Horizon 21.0.0+ / Atmosphère 1.10+ TLS ABI Break (`LNY2`):**
   * Homebrew binaries compiled against `libnx < 4.10` lack the `LNY2` ABI magic (`0x32594E4C`, revision $\ge 1$) in their `MOD0` section and crash immediately on launch due to Thread-Local Storage (TLS) layout changes.
   * Legacy Tesla overlays (such as older 2020 overlay builds) fail on FW 19+ and must be replaced by actively maintained forks (e.g., `proferabg/EdiZon-Overlay` v1.0.15).
3. **System Memory Pool 2 Exhaustion & FW 19+ `ns:ro` Deprecations:**
   * Running co-resident background sysmodules alongside stock `sys-autopilot` v1.5.0 (`Title ID: 4200000000004150`) triggered boot panics (`Error 2001-0131 / 0x10801` on process `am`) on Atmosphère 1.11.1.
   * **Measured Cause:** Stock `sys-autopilot` v1.5.0 allocated a `4 MB` inner heap (`0x400000`) plus a `1 MB` static install buffer (`6.69 MB` total ELF / `6.33 MB` BSS), starving Horizon's tight System Memory Pool 2 at boot. Furthermore, calling deprecated `nsGetApplicationControlData` without updated `ns:ro` permissions triggered `std::abort` (`0100000000000034`) on FW 22.1.0.

### B. Hardcoded Dead Relays & Trackers in P2P Clients
When decentralized networks evolve, hardcoded bootstrap lists turn into self-inflicted denial-of-service vectors:

1. **Unresponsive Nostr Relays in `lnbits/napstr`:**
   * Upstream default relay lists included unmaintained endpoints (and third-party testing on 2026-08-26 reported repeated HTTP 503s on public relays). Without a health circuit breaker, the client spent sockets and stalled catalogue queries waiting on unresponsive relays. Furthermore, updating a hardcoded constant does not automatically clean up local SQLite databases that have already persisted the old defaults. (Proposed hardening in open upstream PR #2).
2. **Defunct BitTorrent Trackers in Stremio `EngineFS` (`server.js`):**
   * Public magnet links routinely carry 15+ dead tracker URLs (e.g., `tracker.example.invalid`, `backup-tracker.example.invalid`).
   * **Measured Failure:** `EngineFS` ran `peerSearch` every 30 seconds (`setInterval(..., 3e4)`), firing unthrottled DNS lookups for every dead tracker on every cycle. Over a WireGuard VPN tunnel, this exhausted Node.js's `UV_THREADPOOL_SIZE` after ~5 minutes of playback (~63 MB downloaded) and dropped active peer wires to zero.

### C. On-Chain Swap Halts & Bonding-Curve Sniper Observations (Aug–Sept 2026)
1. **Cross-Chain Bridge Outages (`Boltz` & `Atomiq Labs`):**
   * On 2026-08-03, `Boltz` announced an indefinite pause on all swap operations, citing escalating automated infrastructure attacks. On 2026-08-12, new operators took over, with swap operations remaining offline during the transition.
   * On 2026-08-20, `Atomiq Labs` took swap routes offline citing AI-assisted attacks.
   * Automated cross-chain workflows that assumed a single non-custodial bridge API would remain live indefinitely were blocked until fallback routes (e.g., accountless fixed-quote services, with explicit acknowledgment of their slower confirmation cadence and different trust boundaries) were integrated.
2. **Launchpad Zero-Dev-Buy Sniper Hypotheses (Empirical On-Chain Test Data):**
   * Community discussions and trading channels in August 2026 suggested that deploying zero-dev-buy tokens on high-speed bonding-curve launchpad contracts reliably attracted profitable bids from automated MEV sniper bots.
   * **Our Empirical On-Chain Sample ($N=60$ consecutive factory deployments, $N=24$ zero-dev-buy):**
     * **87.5% (21/24)** of zero-dev-buy launches in our sample recorded zero subsequent volume (loss of creation fee and gas).
     * Only **4.17% (1/24)** recorded a Block 0–2 purchase greater than $30.
     * **Hypotheses:** On sub-second block time L2 rollups, sniper bots appear to use deployer wallet balance heuristics to filter out micro-funded creators, or contract-level early-block anti-frontrunning mechanics disincentivize immediate bidding.

## 4. What Helped

1. **Archive, Don't Delete, Legacy Artifacts (`trash > rm`):**
   * When cleaning console SD storage, obsolete CFW folders and conflicting sysmodules were moved to a backup archive directory (with device-specific calibration data backed up off-device first) rather than deleted in place.
2. **Scan Binary Headers for ABI Compatibility:**
   * Verify the `LNY2` marker in the `MOD0` section of compiled AArch64 homebrew binaries before deploying to modern Horizon firmware, and shrink background sysmodule BSS allocations (`INNER_HEAP_SIZE` reduced from `4 MB` to `512 KB`, reducing total ELF footprint from `6.69 MB` to `2.11 MB`).
3. **Add Dead-Endpoint Circuit Breakers & Forward Config Migrations:**
   * In Nostr clients, pair forward schema migrations with a health loop that removes unresponsive relays after consecutive failures.
   * In BitTorrent streaming daemons (`EngineFS`), cache any tracker hostname returning `ENOTFOUND`, `ENOENT`, or timeout errors for 10 minutes (`600,000 ms`) so dead domains cannot starve the Node.js DNS threadpool.
4. **Empirically Sample On-Chain Contract Activity Before Building Automation:**
   * Sample recent contract deployments across block history to measure actual base-rate outcomes before building automation around unverified claims.

## 5. Limits
* **Ecosystem State Is Dynamic:** Service availability for bridge providers changes over time; check current status pages and operator announcements directly.
* **Different Trust & Custody Boundaries:** Using an accountless fixed-quote intermediary as a fallback route does not replicate the cryptographic submarine-swap guarantees of non-custodial HTLC/PTLC protocols.
* **Launchpad Samples Are Bounded:** The 60-launch sample reflects a specific point-in-time snapshot and does not represent all market conditions.

## Related Field Notes
* [iPod Nano 3G (A1236) Reverse Engineering & Silicon Bringup](a1236-ipod-nano-3g-reverse-engineering.md) — Hardware bringup and bootloader provenance on legacy silicon.
* [Rabbit R1 Hardware Architecture, Bootloader Unlock & GSI Porting](rabbit-r1-bootloader-unlock-and-gsi.md) — BROM exploits, AVB bypass, and mobile operating system provenance.
* [Agentic Engineering: Managing Long-Running Binary Porting Projects](agent-handoff-and-artifact-gating.md) — Preserving build provenance across long-term development lifecycles.

## 6. Sources & Credit
* Switch Homebrew ABI (`LNY2` in `MOD0`) & `libnx` 4.10+ TLS specification: [switchbrew/libnx](https://github.com/switchbrew/libnx) & [Atmosphère-NX](https://github.com/Atmosphere-NX/Atmosphere)
* Switch `sys-autopilot` slim memory & FW 22.1.0 patches: [TooTallNate/sys-autopilot PR #30](https://github.com/TooTallNate/sys-autopilot/pull/30)
* Nostr P2P audio client relay hardening: [lnbits/napstr PR #2](https://github.com/lnbits/napstr/pull/2)
* Boltz Submarine Swaps & Service Updates: [@Boltzhq August 3, 2026 Announcement](https://x.com/Boltzhq/status/2084311537502630319) regarding indefinite pause of swap infrastructure.
* Atomiq Labs Cross-Chain Protocol: [@atomiqlabs August 20, 2026 Notice](https://x.com/atomiqlabs/status/2090374622357102671) regarding swap routes halt.
* Launchpad On-Chain Activity: [Arbitrum Orbit L2 Framework](https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction) (Empirical on-chain test data across 60 consecutive factory launch events)
