# OBS Open-Mic Acoustic Audio Alignment via FFT Cross-Correlation

## Problem
Broadcasters and audio engineers operating open studio microphones alongside live monitor speakers frequently encounter delayed speaker playback bleeding into the microphone feed. Typical workarounds suffer from severe audio degradation:
* **Aggressive Noise Gates:** Cut off trailing sentences, natural room reverb, and quiet breathing.
* **Software Echo Cancellation (AEC):** Introduces robotic comb-filtering, flanging phase artifacts, and dynamic CPU overhead.
* **Manual "Clap" Calibration:** Eyeballing visual waveforms in video editors yields multi-millisecond errors due to sample rate conversion and frame quantization.

## Environment
* **Platform:** Windows 64-bit workstation.
* **Software:** OBS Studio (64-bit), OBS WebSocket v5 API, Python 3 with `scipy.signal` and `numpy`.
* **Audio Routing:** Windows WASAPI / CoreAudio default output, multi-track audio recording (Track 2: Mic/Aux; Track 4: Clean Desktop Audio).

## What Was Observed

### 1. Packet Timestamp Discontinuities During Live Edits
When adjusting the "Sync Offset" property live in OBS via WebSocket or the Advanced Audio Properties panel, OBS does not re-encode previous buffer frames; instead, it injects presentation timestamp (PTS) discontinuities into the container stream.

Standard raw PCM decoders reading linear samples from disk discard these container PTS jumps, causing subsequent correlation math to measure incorrect cumulative offsets:

```text
Container PTS: [0.000s] ----> [Live Offset Edit +15ms] ----> [0.015s discontinuity]
Raw PCM Reader: Assumes continuous linear stream -> Drift error propagates
```

### 2. Within-Take vs. Between-Take Repeatability
Repeatedly re-initializing the Windows playback audio graph (`SoundPlayer` / media APIs) introduced 10–25 ms of random startup jitter across different recording takes. True acoustic alignment requires analyzing one continuous multi-track take with a looped test signal rather than separate short file takes.

## What Helped

### 1. High-Frequency Logarithmic Chirp Signals
Rather than using impulse clicks or voice claps, the calibration routine generates four quiet 400–2600 Hz logarithmic sine sweeps (chirps). A logarithmic chirp distributes energy evenly per octave (pink noise spectrum), creating a sharp mathematical autocorrelation peak when cross-correlated against room recordings.

### 2. Timeline Reconstruction with FFmpeg `aresample`
To correctly evaluate audio files containing live OBS offset adjustments, the audio stream must be decoded through an asynchronous resampler that honors presentation timestamps:

```bash
ffmpeg -i recording.mkv -map 0:a:0 -af "aresample=async=1:min_hard_comp=0.001:first_pts=0" -f wav mic.wav
ffmpeg -i recording.mkv -map 0:a:1 -af "aresample=async=1:min_hard_comp=0.001:first_pts=0" -f wav desktop.wav
```

`aresample=async=1` inserts silence or trims samples dynamically to lock the output audio samples strictly to the container's PTS timeline.

### 3. FFT Cross-Correlation Analysis
Using `scipy.signal.fftconvolve`, the clean reference chirp is cross-correlated against both the desktop track and the microphone track:

```python
import numpy as np
from scipy import signal
from scipy.io import wavfile

def find_delay(reference_wav, recorded_wav):
    sr_ref, ref_data = wavfile.read(reference_wav)
    sr_rec, rec_data = wavfile.read(recorded_wav)
    
    # Compute cross-correlation via FFT
    correlation = signal.fftconvolve(rec_data, ref_data[::-1], mode='full')
    peak_sample = np.argmax(np.abs(correlation))
    
    # Calculate time offset in milliseconds
    delay_ms = ((peak_sample - (len(ref_data) - 1)) / sr_rec) * 1000.0
    return delay_ms
```

### 4. Verified Settings Result
After running the automated correlation loop:
* **Desktop Audio Sync Offset:** `+8 ms`
* **Mic / Aux Sync Offset:** `0 ms`
* **Resulting Relative Arrival:** `-0.083 ms` (mic relative to desktop, within $\le 0.1\text{ ms}$ sub-millisecond acoustic tolerance).

The speaker soundwave reaches the microphone diaphragm simultaneously with the direct desktop audio stream, eliminating perceived echo in the final mix without applying any gating or digital suppression filters.

## Limits
* **Integer Offset Granularity in OBS:** While FFT cross-correlation measures relative arrival down to sub-sample precision (e.g. `-0.083 ms`), OBS Studio's Advanced Audio Properties Sync Offset field accepts only integer millisecond values (e.g. `+8 ms`). Any residual sub-millisecond arrival delta ($<1\text{ ms}$) is well below the threshold of human echo perception and phase distortion in voice mixes.
* **Physical Distance Dependent:** Sound travels in air at approximately $343\text{ m/s}$ ($\approx 0.029\text{ ms per cm}$, or $\approx 2.9\text{ ms per meter}$). If the physical distance between the monitor speakers and the microphone changes significantly, the physical acoustic delay changes accordingly.
* **Audio Driver Clock Drift:** Over multi-day sessions, separate USB audio interfaces and onboard motherboard DACs can experience microscopic hardware crystal oscillator drift.

## Related Field Notes
* [NVENC Hardware Encoding Architecture & Session Starvation](nvenc-hardware-encoding-architecture.md) — GPU encoder session allocation and broadcast pipeline limits.
* [OBS Studio: Cutting Inactive Browser and Media Source Overhead](obs-inactive-browser-and-media-sources.md) — Auditing and toggling inactive OBS sources over WebSocket.
* [Real-Time WebGL Biometric Stream Overlays & Socket Recovery](webgl-hyperate-adrenaline-overlay.md) — WebGL canvas rendering and OBS scene composition.

## Sources & Credit
* [FFmpeg Filter Documentation](https://ffmpeg.org/ffmpeg-filters.html#aresample-1) for `aresample` async timestamp synchronization.
* [SciPy Signal Processing Documentation](https://docs.scipy.org/doc/scipy/reference/signal.html) for FFT cross-correlation (`scipy.signal.fftconvolve`).
