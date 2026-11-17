#!/usr/bin/env python3
"""Print the PipeWire sink name and the speaker/headphone route descriptions.

EasyEffects autoload profiles are keyed by `<node name>:<route description>`, and
the route description is translated by PipeWire, so it cannot be hardcoded in
the repo. This resolves it from the running graph, matching the route names
(`analog-output-speaker`, `analog-output-headphones`) instead of their text.

Output: shell-assignable KEY=value lines.
"""

import json
import subprocess
import sys


def load_dump():
    out = subprocess.run(["pw-dump"], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def route_info(route):
    """SPA serialises route properties as a flat [n, k, v, k, v, ...] array."""
    info = route.get("info") or []
    props = {}
    if info and isinstance(info[0], int):
        flat = info[1:]
        for i in range(0, len(flat) - 1, 2):
            props[flat[i]] = flat[i + 1]
    return props


def find_sink(dump):
    devices = {d["id"]: d for d in dump if d["type"] == "PipeWire:Interface:Device"}
    candidates = []
    for node in dump:
        if node["type"] != "PipeWire:Interface:Node":
            continue
        props = node.get("info", {}).get("props", {})
        if props.get("media.class") != "Audio/Sink":
            continue
        device_id = props.get("device.id")
        if not device_id or device_id not in devices:
            continue
        device = devices[device_id]
        routes = (device.get("info", {}).get("params") or {}).get("EnumRoute") or []
        outputs = [r for r in routes if r.get("direction") == "Output"]
        speakers = [r for r in outputs if "speaker" in r.get("name", "")]
        headphones = [r for r in outputs if "headphones" in r.get("name", "")]
        if speakers and headphones:
            candidates.append((node, device, speakers[0], headphones[0]))
    if not candidates:
        return None
    # Prefer the analog profile: HDMI sinks expose no speaker/headphone pair.
    analog = [c for c in candidates if "analog" in c[0]["info"]["props"].get("device.profile.name", "")]
    return (analog or candidates)[0]


def main():
    dump = load_dump()
    found = find_sink(dump)
    if found is None:
        print("error: no sink with speaker and headphone routes found", file=sys.stderr)
        return 1
    node, device, speaker, headphone = found
    props = node["info"]["props"]
    print(f"DEVICE_NAME={props.get('node.name', '')}")
    print(f"DEVICE_DESCRIPTION={props.get('node.description', '')}")
    print(f"SPEAKER_ROUTE={speaker['description']}")
    print(f"HEADPHONE_ROUTE={headphone['description']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
