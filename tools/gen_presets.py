#!/usr/bin/env python3
"""Generate the EasyEffects presets in this repo.

Every key and enum label mirrors easyeffects v8.1.2 (src/*_preset.cpp and the
kcfg definition files), so the presets load without falling back to defaults.

Usage: python3 tools/gen_presets.py [output-dir]
"""

import json
import pathlib
import sys

DEFAULT_OUT = pathlib.Path(__file__).resolve().parent.parent / "presets"

BASE = {
    "bypass": False,
    "input-gain": 0.0,
    "output-gain": 0.0,
}


def band(type_, freq, gain=0.0, q=1.41, width=4.0, slope="x1", mode="RLC (BT)"):
    return {
        "type": type_,
        "mode": mode,
        "slope": slope,
        "solo": False,
        "mute": False,
        "gain": gain,
        "frequency": freq,
        "q": q,
        "width": width,
    }


def high_pass(frequency, slope):
    """Dedicated filter plugin. The equalizer's Hi-pass band is unusable: LSP
    recalculates the Q per stage and ends up with a ~30 dB resonance at the
    cutoff frequency."""
    return {
        **BASE,
        "frequency": frequency,
        "width": 4.0,
        "gain": 0.0,
        "quality": 0.71,
        "balance": 0.0,
        "type": "High-pass",
        "mode": "RLC (BT)",
        "equal-mode": "IIR",
        "slope": slope,
    }


def equalizer(bands, output_gain=0.0, mode="IIR"):
    bands = bands + [band("Off", 1000.0) for _ in range(8 - len(bands))]
    channel = {f"band{i}": b for i, b in enumerate(bands)}
    return {
        **BASE,
        "output-gain": output_gain,
        "mode": mode,
        "split-channels": False,
        "balance": 0.0,
        "pitch-left": 0.0,
        "pitch-right": 0.0,
        "num-bands": len(bands),
        "left": json.loads(json.dumps(channel)),
        "right": json.loads(json.dumps(channel)),
    }


def bass_enhancer(amount, harmonics, scope, floor, floor_active=True):
    return {
        **BASE,
        "amount": amount,
        "harmonics": harmonics,
        "scope": scope,
        "floor": floor,
        "blend": 0.0,
        "floor-active": floor_active,
    }


def exciter(amount, harmonics, scope, ceil, ceil_active=True):
    return {
        **BASE,
        "amount": amount,
        "harmonics": harmonics,
        "scope": scope,
        "ceil": ceil,
        "blend": 0.0,
        "ceil-active": ceil_active,
    }


def crossfeed(fcut=700, feed=4.5):
    return {**BASE, "fcut": fcut, "feed": feed}


def autogain(target=-16.0, history=10, silence=-70.0):
    return {
        **BASE,
        "target": target,
        "silence-threshold": silence,
        "maximum-history": history,
        "reference": "Geometric Mean (MSI)",
        "force-silence": False,
    }


def stereo_tools(stereo_base=0.15):
    return {
        **BASE,
        "balance-in": 0.0,
        "balance-out": 0.0,
        "softclip": False,
        "mutel": False,
        "muter": False,
        "phasel": False,
        "phaser": False,
        "mode": "LR > LR (Stereo Default)",
        "side-level": 0.0,
        "side-balance": 0.0,
        "middle-level": 0.0,
        "middle-panorama": 0.0,
        "stereo-base": stereo_base,
        "delay": 0.0,
        "sc-level": 1.0,
        "stereo-phase": 0.0,
        "dry": -80.01,
        "wet": 0.0,
    }


def limiter(threshold=-1.0, attack=1.0, release=10.0, lookahead=2.0):
    return {
        "bypass": False,
        "input-gain": 0.0,
        "output-gain": 0.0,
        "mode": "Herm Thin",
        "oversampling": "None",
        "dithering": "None",
        "sidechain-type": "Internal",
        "lookahead": lookahead,
        "attack": attack,
        "release": release,
        "threshold": threshold,
        "gain-boost": False,
        "stereo-link": 100.0,
        "alr": False,
        "sidechain-preamp": 0.0,
    }


# Built-in speakers of a ThinkPad E14 Gen 2 (Realtek ALC257, 2 small drivers).
# Dolby Audio "Music/Dynamic" behaviour: extra body, recessed mud, forward
# presence, air on top, psychoacoustic bass for the octave the drivers lack.
SPEAKERS = {
    "output": {
        "blocklist": [],
        "plugins_order": [
            "filter#0",
            "equalizer#0",
            "bass_enhancer#0",
            "exciter#0",
            "autogain#0",
            "stereo_tools#0",
            "limiter#0",
        ],
        "filter#0": high_pass(60.0, "x2"),
        "equalizer#0": equalizer(
            [
                band("Lo-shelf", 160.0, 2.5, q=0.7),      # body / punch
                band("Bell", 550.0, -2.0, q=1.1),         # de-mud
                band("Bell", 2700.0, 3.0, q=1.2),         # presence / dialogue
                band("Hi-shelf", 7000.0, 2.5, q=0.7),     # air
            ],
            output_gain=-3.0,
        ),
        "bass_enhancer#0": bass_enhancer(2.5, 9.0, 150.0, 30.0),
        "exciter#0": exciter(2.5, 9.0, 6500.0, 15000.0),
        "autogain#0": autogain(),
        "stereo_tools#0": stereo_tools(0.15),
        "limiter#0": limiter(),
    }
}

# Dolby Atmos for headphones is mostly mild loudness plus out-of-head imaging;
# crossfeed approximates speaker crosstalk with zero latency.
HEADPHONES = {
    "output": {
        "blocklist": [],
        "plugins_order": ["filter#0", "equalizer#0", "crossfeed#0", "limiter#0"],
        "filter#0": high_pass(25.0, "x2"),
        "equalizer#0": equalizer(
            [
                band("Lo-shelf", 90.0, 2.5, q=0.7),
                band("Bell", 1800.0, -1.0, q=1.0),
                band("Bell", 3200.0, 1.5, q=1.2),
                band("Hi-shelf", 8000.0, 1.5, q=0.7),
            ],
            output_gain=-2.0,
        ),
        "crossfeed#0": crossfeed(700, 4.5),
        "limiter#0": limiter(threshold=-1.5),
    }
}


def main():
    out_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, preset in (
        ("Dolby-ThinkPad-Speakers", SPEAKERS),
        ("Dolby-ThinkPad-Headphones", HEADPHONES),
    ):
        path = out_dir / f"{name}.json"
        path.write_text(json.dumps(preset, indent=4) + "\n")
        print(f"written {path}")


if __name__ == "__main__":
    main()
