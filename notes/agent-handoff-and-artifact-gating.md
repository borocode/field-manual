# Agentic Engineering: Managing Long-Running Binary Porting Projects with Handoff & Manifest Files

## 1. The Problem
During a multi-week static binary recompilation and porting project (translating a legacy PowerPC binary into C/AArch64 and debugging its custom graphics pipeline across an emulator and physical target hardware), a single coding-agent thread ran across **140,000+ JSONL log lines (~1.99 GB on disk)** and grew to roughly **197,000 input tokens per turn**.

As the project accumulated dozens of experimental ~75 MB binaries and multi-hundred-megabyte runtime trace logs, three operational failures kept recurring:
1. **Ambiguous Binary Identity:** Both the emulator and target device UI displayed the embedded application metadata string (`v0.1.0`) rather than the filename. When multiple diagnostic builds were staged, neither the human operator nor a new agent session could tell from a window screenshot which binary was actually running.
2. **Stale Handoff Files:** Older summary files (`CURRENT_STATUS.md`, `STATUS.md`) remained in the root directory after newer work moved to `HANDOFF.md`. When a second agent inspected the workspace or parsed the pre-fork session log, it read the older status file and recommended running a week-old diagnostic build that had already been superseded.
3. **Unbounded Runtime Logs & Unverified Rebuilds:** Early diagnostic builds wrote over **227 MB (`2,000,000+` lines)** to the shared `runtime-startup.log` file on the target SD path, making log inspection slow and tempting agents to compile new speculative builds before verifying whether the previous staged build had actually been executed.

## 2. Environment
* **Workflow:** Multi-session collaboration between a human operator and local coding agents working in a shared project directory
* **Build Artifacts:** Cross-compiled AArch64 binaries (~75 MB each) deployed to both a local desktop emulator and a physical target over LAN/FTP
* **Host OS:** Windows 11 with MSYS2 / devkitA64 cross-compilation toolchain and CMake/CTest host regression tests

## 3. What Was Observed
* **Context Size vs. State Clarity:** Even with a 258K-token context window and prompt caching (~2.93B cumulative cached input tokens over 6 weeks, ~68.3M active goal tokens), a huge conversation history did not prevent state confusion—and on fixed-price subscription tiers, sending ~197K input tokens per tool call rapidly exhausted rolling 5-hour rate limits.
* **Filename Collisions:** Overwriting a single `app.bin` path during iterative experiments made it impossible to correlate historical runtime log segments with the exact compiler flags or source patches that produced them, especially if the emulator still held a file lock on the binary during packaging.
* **Host Test Drift:** Relying on cached `CTest` metadata failed when directory paths shifted, whereas running the compiled host test executables directly via a tiny wrapper script succeeded deterministically.

## 4. What Helped

### 1. Maintain One Authoritative `HANDOFF.md` + `BUILD_MANIFEST.md` (and Deprecate Old Status Files)
Instead of relying on chat history or scattering multiple `STATUS.md` / `CURRENT_STATUS.md` files in the repo root, keep **two canonical files** and explicitly mark any older notes as historical at the top:

* **`BUILD_MANIFEST.md`:** A table mapping every built candidate's **Label**, **Purpose/Flags**, **Exact Staged Path**, and **SHA-256 hash**.
  ```markdown
  | Label | Purpose | Staged Path | SHA-256 |
  | :--- | :--- | :--- | :--- |
  | `visual-baseline-20261023` | Known-good visual baseline; do not overwrite | `build/baseline/app-baseline.bin` | `7D0FB4F5...` |
  | `vtxfast-prof-20261025` | Fast vertex decode + `PERF_PROFILE=1` timers | `build/vtxfast-prof/app-vtxfast-prof.bin` | `CD553ECE...` |
  ```
* **`HANDOFF.md`:** Records the **Current Verified Baseline** (with measured metrics), **Rejected Experiments** (and why they failed, so the next agent session never repeats them), and the **Single Next Measurement Gate**.

### 2. Embed Distinct Build Markers in Both Metadata and Runtime Logs
Never rely on a generic `v0.1.0` title or a filename alone to prove which binary is running:
1. Set a distinct visible title/version string in the binary's packaging metadata (e.g., `v0.1.0-rdiag`, `v0.1.0-vtxfast`) so launcher menus and window titles are unambiguous.
2. Print an explicit `build=<label>` line at the start of every runtime log session and require the agent to verify that marker before attributing performance counters to a candidate.
3. Verify both **file size and SHA-256** after packaging (packaging or linker exit code `0` alone is not proof that the target file was updated, especially if an emulator has the file open).

### 3. Cap Per-Launch Diagnostic Logs in Code
To prevent a slow or stuck run from writing 200+ MB logs that choke agent file readers and SD cards:
* Enforce a hard per-launch byte/line cap (for example, **2 MiB per launch**) in the runtime logger, followed by a single `cap_reached` marker.
* For high-frequency events (such as renderer draw rejections), log only sparse checkpoints (e.g., the first 8 occurrences, powers of two, and every $16,384\text{th}$ occurrence) rather than every frame.

### 4. Gate Next Builds on Measured Runtime Evidence
Write an explicit rule in `HANDOFF.md`:
> *"Do not compile or stage another optimization candidate until the currently staged build has been verified via its `build=` runtime marker in a settled test window."*

If the test requires manual user input or hardware access that is currently unavailable, pause the agent goal rather than letting an automated continuation loop poll unchanged log files.

### 5. Rotate Threads + Split Model Tiers by Task
* When a thread's per-turn input context grows past ~50K–100K tokens, start a fresh thread seeded with `HANDOFF.md` and `BUILD_MANIFEST.md` (or use `/compact` and verify the retained summary against those two files).
* Use a lower-cost model tier for routine build/log/test commands, reserving frontier reasoning models for the specific turns that design or debug complex code changes.

## 5. Limits
* **Manual Discipline Required:** A `HANDOFF.md` file only works if old summary files (`CURRENT_STATUS.md`, etc.) are either deleted, archived into a `history/` subfolder, or updated to point directly to `HANDOFF.md`. Having two competing status files in the root directory is worse than having none.
* **Source Tree Snapshots without Git:** In projects that are not tracked in Git (or contain large generated C chunks), restoring the working tree after a rejected experiment requires saving explicit source snapshots (`src-<candidate>/`) alongside the binary in `build/` and verifying hashes before and after each test.
* **Quota Math Varies by Provider:** Token usage reported by local session logs (`total_tokens` including cached prefixes) and token usage reported by provider goal trackers (uncached + output tokens) measure different quantities, and neither maps 1:1 to undocumented subscription rate-limit formulas.

## Related Field Notes
* [Multi-Agent Relay Architecture: The Cloud Architect to Local Compiler Pattern](multi-agent-relay-architecture.md) — Multi-agent compiler loops, context isolation, and disk truth.
* [Autonomous Agent Monetization: Whop MCP vs. L402 Lightning Tollbooths](agent-monetization-whop-mcp-vs-l402-tollbooths.md) — Agent tool harnesses and operational boundaries.
* [Provenance & Postmortems: Defunct Tools & Protocols](defunct-protocols-and-homebrew-provenance.md) — Preserving build provenance across long-term development lifecycles.

## 6. Sources & Credit
* [NIST FIPS 180-4 Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) (SHA-256).
* Synthesized from multi-agent static binary recompilation and hardware debugging sessions.
