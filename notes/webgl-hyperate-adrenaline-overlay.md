# Real-Time WebGL Biometric Stream Overlays & Socket Recovery

## Problem
Live broadcasting setups displaying real-time biometric telemetry (such as Bluetooth Low Energy heart rate data) over a full-canvas WebGL browser source encounter two critical failure modes:
1. **Silent WebSocket Zombie Connections:** Upstream telemetry WebSocket servers frequently continue exchanging transport-level ping/pong heartbeats even when the underlying Bluetooth peripheral has disconnected or stopped pushing biometric frames. The browser source remains technically "connected," but the visual overlay remains frozen at a stale reading indefinitely.
2. **OBS Scene Group Alpha Compounding:** When a full-screen ($2560 \times 1440$) WebGL browser source is organized inside an OBS Scene Group that has an opacity filter applied, standard browser source rendering double-multiplies alpha channels, washing out color saturation and causing unnecessary compositing load.

## Environment
* **Platform:** Linux / Windows streaming workstations running OBS Studio (64-bit).
* **Source:** 2D/3D WebGL Canvas (`2560 x 1440` transparent viewport).
* **Protocol:** WebSockets (WSS) streaming JSON biometric telemetry from BLE heart rate devices (e.g., HypeRate API).

## What Was Observed

### 1. The "Ghost Socket" Deadlock
During multi-hour broadcasts, if a heart rate sensor drops off the network (e.g. battery swap, sleep mode), the WebSocket connection stays open in the browser runtime. Because the server continues transmitting transport ping frames, standard `onclose` and `onerror` event listeners never fire:

```text
[Sensor Powered Off] 
         │
         ▼
[Upstream Gateway] ──(HTTP/WS Ping/Pong Active)──> [OBS Browser Source]
         │                                                    │
(Zero HR telemetry packets)                                    ▼
                                                     (Shader frozen at 94 BPM forever)
```

### 2. Scene Graph Opacity Inconsistencies
OBS Scene Groups allow broadcasters to adjust group-level visibility. However, applying a `0.28` opacity filter to a parent Group containing a WebGL browser source diminishes translucent shader layers non-linearly, rendering procedural depth effects completely invisible.

## What Helped

### 1. Dual-Threshold Watchdog with Hard Socket Termination
To eliminate zombie sockets without requiring human intervention or an OBS restart, a client-side freshness watchdog was implemented in JavaScript:
* **Soft Timeout (60 Seconds):** If no fresh telemetry frame arrives within 60 seconds, the shader smoothly fades all border elements to alpha 0.0, hiding stale metrics from the stream.
* **Hard Reset (90 Seconds):** If 90 seconds elapse without a valid reading, the script explicitly calls `socket.close()`. This deliberate termination triggers the client's automated backoff-and-reconnect handler, re-subscribing cleanly to the upstream gateway:

```javascript
// Telemetry Freshness & Zombie Socket Watchdog
let lastReadingTimestamp = Date.now();
const STALE_HIDE_MS = 60000;
const ZOMBIE_KILL_MS = 90000;

function onTelemetryPacket(data) {
  if (data && data.heartRate > 0) {
    lastReadingTimestamp = Date.now();
    updateShaderUniforms(data.heartRate);
  }
}

setInterval(() => {
  const elapsed = Date.now() - lastReadingTimestamp;
  
  if (elapsed >= ZOMBIE_KILL_MS) {
    console.warn("Telemetry socket zombie detected. Forcing socket termination.");
    lastReadingTimestamp = Date.now(); // Prevent repeat calls in same cycle
    if (activeSocket) {
      activeSocket.close(); // Triggers automated onclose reconnection
    }
  } else if (elapsed >= STALE_HIDE_MS) {
    fadeOverlayToZero();
  }
}, 5000);
```

### 2. URL-Driven Group Opacity Compensation
Rather than hardcoding opacity values into the shader, the browser source URL accepts a dynamic `groupOpacity` query parameter:

```text
file:///path/to/overlay.html?view=graph&groupOpacity=0.28
```

The WebGL fragment shader normalizes internal alpha calculations inversely against the parent container's opacity multiplier (`effectiveAlpha = targetAlpha / groupOpacity`), preserving correct color saturation and translucent layering regardless of OBS scene hierarchy.

### 3. Procedural Multi-Plane Shader Architecture
To keep GPU utilization minimal across 60 FPS live rendering at $2560 \times 1440$:
* The center of the canvas is discarded in the fragment shader (`discard` instruction) when distance from the edge exceeds threshold, aborting downstream framebuffer and alpha blend writes for ~80% of the screen area.
* Telemetry pulses are rendered as smoothed procedural sine curves rather than loading external texture atlases, avoiding VRAM bandwidth bottlenecks.

## Limits
* **Browser Source Process Isolation:** If the underlying Chromium Embedded Framework (CEF) crashes, OBS must be told to refresh the browser source cache via the OBS WebSocket `PressInputPropertiesButton` API.
* **Network Flaps During Reconnect:** Rapid back-to-back reconnections can trigger rate limits on public telemetry gateways; a 3–5 second exponential backoff jitter should be maintained.

## Related Field Notes
* [OBS Studio: Cutting Inactive Browser & Media Source Overhead](obs-inactive-browser-and-media-sources.md) — Auditing and managing browser source memory overhead.
* [OBS Open-Mic Acoustic Audio Alignment via FFT Cross-Correlation](obs-acoustic-audio-alignment.md) — Synchronizing audio and video production pipelines.
* [NVENC Hardware Encoding Architecture & Session Starvation](nvenc-hardware-encoding-architecture.md) — Managing GPU encoding load during live broadcasts.

## Sources & Credit
* [Chromium Embedded Framework (CEF) Documentation](https://github.com/chromiumembedded/cef) for browser source architecture.
* [HypeRate WebSocket API specification](https://www.hyperate.io/).
