#!/usr/bin/env python3
"""Measure the response EasyEffects applies right now, with single tones.

Plays a short tone per frequency at a low level into the Easy Effects sink and
records the monitor of the hardware sink, so the whole chain is included. The
magnitude is read at the fundamental only, which keeps the harmonic generators
(bass enhancer, exciter) from skewing the result.

Run it twice -- once with the preset loaded, once with "Nothing" -- and subtract
the numbers to get the curve of the preset:

    python3 tools/measure_response.py            # with the preset loaded
    easyeffects -l Nothing
    python3 tools/measure_response.py            # baseline
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
import wave

import numpy as np

RATE = 48000
FREQS = [50, 63, 80, 125, 200, 315, 500, 800, 1250, 2000, 3150, 5000, 8000, 12000, 16000]
TONE_SECONDS = 1.6
AMPLITUDE = 0.04


def hardware_sink():
    out = subprocess.run(["pw-dump"], capture_output=True, text=True, check=True).stdout
    for obj in json.loads(out):
        if obj["type"] != "PipeWire:Interface:Node":
            continue
        props = obj.get("info", {}).get("props", {})
        if props.get("media.class") == "Audio/Sink" and "analog" in props.get("device.profile.name", ""):
            return props["node.name"]
    raise SystemExit("error: no analog sink found; pass --device")


def write_tone(path, freq):
    t = np.arange(int(RATE * TONE_SECONDS)) / RATE
    mono = AMPLITUDE * np.sin(2 * np.pi * freq * t)
    stereo = np.repeat(mono[:, None], 2, axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((stereo * 32767).astype("<i2").tobytes())


def capture(path, monitor, seconds):
    rec = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "pulse",
         "-i", monitor, "-t", str(seconds), "-ar", str(RATE), "-ac", "2", path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.6)
    subprocess.run(["pw-play", "--target", "easyeffects_sink", path[:-len(".rec.wav")]], check=True)
    rec.wait(timeout=30)
    with wave.open(path) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float)
    return data.reshape(-1, 2).mean(axis=1) / 32768.0


def fundamental(signal, freq):
    seg = signal[int(0.9 * RATE): int(0.9 * RATE) + int(1.2 * RATE)]
    seg = seg * np.hanning(len(seg))
    spec = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(len(seg), 1 / RATE)
    k = int(np.argmin(np.abs(freqs - freq)))
    return float(20 * np.log10(spec[max(0, k - 1):k + 2].max() + 1e-12))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", help="hardware sink node name (default: autodetect analog)")
    args = parser.parse_args()
    sink = args.device or hardware_sink()
    monitor = sink + ".monitor"
    print(f"# sink: {sink}")
    with tempfile.TemporaryDirectory() as tmp:
        for freq in FREQS:
            tone = f"{tmp}/tone.wav"
            write_tone(tone, freq)
            rec = tone + ".rec.wav"
            level = fundamental(capture(rec, monitor, TONE_SECONDS + 1.0), freq)
            print(f"{freq:6d} Hz {level:7.2f} dB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
