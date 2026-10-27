# OBS Studio: Cutting Inactive Browser and Media Source Overhead via `obs-websocket`

## 1. The Problem
On a streaming workstation running OBS Studio with a large scene collection accumulated over months of streaming (measured from our own studio profile), OBS was holding roughly **3.7 GB of working-set memory** (`obs64.exe` plus child processes), **25,000+ OS handles**, and **21 separate `obs-browser-page.exe` child processes** even while sitting idle on a single scene without streaming or recording.

In addition, the OBS log file (`%APPDATA%\obs-studio\logs`) showed continuous background network connection attempts every few seconds to local RTMP, SRT, and HTTP camera endpoints that were currently powered off.

## 2. Environment
* **OS:** Windows 11 (64-bit)
* **Application:** OBS Studio (64-bit, `obs64.exe`) with built-in `obs-browser` (Chromium Embedded Framework) and `obs-websocket` v5 enabled (`127.0.0.1:4455`)
* **Scene Collection Size:** Large broadcast profile with 20+ scenes containing over 20 browser and media inputs

## 3. What Was Observed
Inspecting the latest OBS startup/session log and querying the live input settings over `obs-websocket` (`GetInputList` + `GetInputSettings`) revealed three distinct sources of background resource consumption:

1. **Persistent Chromium Browser Sources (`shutdown: false`):**
   Out of 11 browser sources across the scenes, 9 were visual overlays or web embeds (e.g., remote camera feeds, chat overlays, status widgets, and web pages left in secondary scenes) that had **Shutdown source when not visible** (`shutdown`) unset or set to `false`. One older scene's browser source was stuck on an interactive challenge page, continuously executing JavaScript in the background.
2. **Inactive Network Media Sources Polling Offline Endpoints (`close_when_inactive: false`):**
   Six `ffmpeg_source` inputs pointed to network streams (`rtmp://<LAN_OR_VPN_HOST>/...`, `srt://<LAN_HOST>:<PORT>`, `http://<LAN_HOST>/webcam`) that were offline during normal desktop use. Because `close_when_inactive` was `false`, OBS kept polling and failing to connect in the background regardless of which scene was active.
3. **Duplicate and Legacy Scene Items in the Primary Scene:**
   The primary scene had accumulated over 30 top-level scene items (over 45 including group children), including multiple disabled or overlapping capture layers from older hardware setups.

## 4. What Helped

### Step 1: Audit Browser and Media Sources via `obs-websocket` v5
Instead of clicking through dozens of scenes manually in the UI, we queried `obs-websocket` using Python (`websocket-client`) to list every `browser_source` and `ffmpeg_source` and inspect its current settings.

> **Important before modifying settings:** `SetInputSettings` over `obs-websocket` updates OBS's live scene collection state, which OBS persists to `%APPDATA%\obs-studio\basic\scenes\<CollectionName>.json`. Back up that `.json` file before running bulk changes.

```python
# Inspect browser_source and ffmpeg_source lifecycle flags via obs-websocket v5
# Requires: pip install websocket-client
import base64, hashlib, json, websocket

OBS_WS_URL = "ws://127.0.0.1:4455"
OBS_WS_PASSWORD = "<YOUR_OBS_WEBSOCKET_PASSWORD>"

def connect_obs():
    ws = websocket.create_connection(OBS_WS_URL, timeout=5)
    hello = json.loads(ws.recv())
    auth_info = hello["d"].get("authentication")
    identify = {"op": 1, "d": {"rpcVersion": 1}}
    if auth_info:
        secret = base64.b64encode(
            hashlib.sha256((OBS_WS_PASSWORD + auth_info["salt"]).encode()).digest()
        ).decode()
        auth = base64.b64encode(
            hashlib.sha256((secret + auth_info["challenge"]).encode()).digest()
        ).decode()
        identify["d"]["authentication"] = auth
    ws.send(json.dumps(identify))
    ws.recv()  # Identified (op 2)
    return ws

def call_obs(ws, request_type, request_data=None, req_id="1"):
    payload = {"op": 6, "d": {"requestType": request_type, "requestId": req_id}}
    if request_data:
        payload["d"]["requestData"] = request_data
    ws.send(json.dumps(payload))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("op") == 7 and msg["d"]["requestId"] == req_id:
            status = msg["d"].get("requestStatus", {})
            if not status.get("result", False):
                code = status.get("code")
                comment = status.get("comment", "Unknown error")
                raise RuntimeError(f"OBS request '{request_type}' failed ({code}): {comment}")
            return msg["d"].get("responseData", {})

# Audit current settings across all browser and media inputs
ws = connect_obs()
try:
    for kind in ("browser_source", "ffmpeg_source"):
        inputs = call_obs(ws, "GetInputList", {"inputKind": kind}).get("inputs", [])
        for item in inputs:
            name = item["inputName"]
            settings = call_obs(ws, "GetInputSettings", {"inputName": name}).get("inputSettings", {})
            print(kind, name, {
                "shutdown": settings.get("shutdown"),
                "close_when_inactive": settings.get("close_when_inactive"),
                "is_local_file": settings.get("is_local_file"),
            })
finally:
    ws.close()
```

### Step 2: Apply Targeted Lifecycle Settings
We enabled `shutdown: true` on the 9 visual browser sources while deliberately **excluding** audio-critical sources (such as TTS readers and stream alert boxes that need to play sound or stay connected across scene switches). For inactive `ffmpeg_source` inputs, enabling `close_when_inactive: true` stops background decoder threads and socket reconnect loops when the source is not rendered:

> **Prerequisite:** This snippet relies on the `connect_obs` and `call_obs` helper functions defined in Step 1. Run it in the same Python session after Step 1, or include those function definitions at the top of your script.

```python
# Apply lifecycle updates across audited sources
VISUAL_BROWSER_SOURCES = [
    # Replace with the exact inputName values from your audit
    "Example Visual Overlay",
    "Example Remote Camera Ninja",
]

INACTIVE_MEDIA_SOURCES = [
    # Replace with inactive background video loops or offline network feeds
    "Example Network Stream",
    "Example Background Video",
]

ws = connect_obs()
try:
    for name in VISUAL_BROWSER_SOURCES:
        call_obs(ws, "SetInputSettings", {
            "inputName": name,
            "inputSettings": {"shutdown": True},
            "overlay": True,
        })
        print(f"Set shutdown=True on: {name}")

    for name in INACTIVE_MEDIA_SOURCES:
        call_obs(ws, "SetInputSettings", {
            "inputName": name,
            "inputSettings": {"close_when_inactive": True},
            "overlay": True,
        })
        print(f"Set close_when_inactive=True on: {name}")
finally:
    ws.close()
```

### Observed Result on This Machine
Immediately after applying those settings (without restarting OBS or switching the active scene):
* `obs-browser-page.exe` child process count dropped from **21 to 12**.
* Cumulative working-set memory across `obs64.exe` and its Chromium helper processes dropped from **~3,724 MB to ~1,478 MB** (measured via Windows Task Manager / `Get-Process` working set as CEF discarded inactive page contexts).
* Background TCP/SRT reconnect warnings in the OBS log stopped for the inactive network media sources.

### Rollback
Either restore your backed-up scene collection `.json` file while OBS is closed, or run `SetInputSettings` with `{"shutdown": False}` / `{"close_when_inactive": False}` (`"overlay": True`) for any source that needs to stay warm in the background.

## 5. Limits
* **Single-Machine Memory Figures:** The drop from `3,724 MB` to `1,478 MB` reflects the specific pages loaded in those 9 Chromium instances and OS working-set reclamation at that moment; savings will vary depending on how heavy your browser sources are.
* **Scene Transition Reload Delay:** When `shutdown: true` is enabled on a `browser_source`, switching to a scene that uses it (or toggling its visibility on) forces Chromium to reload the URL from scratch. This causes a brief blank/pop-in delay and resets any in-page JavaScript state.
* **WebRTC / VDO.Ninja Re-Handshake:** Enabling `shutdown: true` on a VDO.Ninja browser source disconnects the WebRTC peer connection when you leave the scene. If you switch back and forth frequently during a live broadcast, keep `shutdown: false` on active camera feeds during the stream and only shut down unused scenes.
* **Audio and Alert Overlays:** Do **not** set `shutdown: true` on browser sources that play audio cues, TTS, or event alerts across scenes unless they are present and visible in every scene you use.

## Related Field Notes
* [NVENC Hardware Encoding Architecture & Session Starvation](nvenc-hardware-encoding-architecture.md) — Monitoring GPU encoder session limits and preventing handle leaks.
* [Real-Time WebGL Biometric Stream Overlays & Socket Recovery](webgl-hyperate-adrenaline-overlay.md) — Handling browser source lifecycles and scene group alpha in OBS.
* [OBS Open-Mic Acoustic Audio Alignment via FFT Cross-Correlation](obs-acoustic-audio-alignment.md) — Time-aligning speaker output with microphone input in OBS scenes.

## 6. Sources & Credit
* [OBS Studio `obs-websocket` 5.x Protocol Documentation](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md) (`GetInputList`, `GetInputSettings`, `SetInputSettings`)
* [OBS Browser Plugin (`obs-browser`) Source & Settings Reference](https://github.com/obsproject/obs-browser)
