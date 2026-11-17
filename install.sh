#!/usr/bin/env bash
#
# Install the Dolby-style EasyEffects presets for this machine.
#
#   ./install.sh              install presets + autoload, restart EasyEffects
#   ./install.sh --no-restart install without touching the running instance
#   ./install.sh --dry-run    show what would be written
#   ./install.sh --uninstall  remove everything this script installed
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/easyeffects"
PRESET_DIR="$DATA_DIR/output"
AUTOLOAD_DIR="$DATA_DIR/autoload/output"
SPEAKERS_PRESET="Dolby-ThinkPad-Speakers"
HEADPHONES_PRESET="Dolby-ThinkPad-Headphones"

DRY_RUN=0
RESTART=1
UNINSTALL=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --no-restart) RESTART=0 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

write_autoload() {
  local device="$1" description="$2" route="$3" preset="$4"
  local file="$AUTOLOAD_DIR/${device}:${route}.json"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] autoload $file -> $preset"
    return
  fi
  python3 - "$file" "$device" "$description" "$route" "$preset" <<'PY'
import json, pathlib, sys
path, device, description, route, preset = sys.argv[1:6]
pathlib.Path(path).write_text(json.dumps({
    "device": device,
    "device-description": description,
    "device-profile": route,
    "preset-name": preset,
}, indent=4) + "\n")
PY
  echo "  autoload $(basename "$file") -> $preset"
}

if [[ "$UNINSTALL" == "1" ]]; then
  for preset in "$SPEAKERS_PRESET" "$HEADPHONES_PRESET"; do
    rm -fv "$PRESET_DIR/$preset.json"
  done
  if [[ -d "$AUTOLOAD_DIR" ]]; then
    find "$AUTOLOAD_DIR" -name '*.json' -print0 2>/dev/null |
      while IFS= read -r -d '' file; do
        if grep -q '"preset-name": "Dolby-ThinkPad' "$file"; then
          rm -fv "$file"
        fi
      done
  fi
  echo "Presets removed. EasyEffects keeps the last loaded one until you switch to 'Nothing'."
  exit 0
fi

if ! command -v easyeffects >/dev/null 2>&1; then
  echo "warning: easyeffects is not installed (Ubuntu: sudo apt install easyeffects)" >&2
fi
if ! command -v pw-dump >/dev/null 2>&1; then
  echo "error: pw-dump not found; this needs a PipeWire session" >&2
  exit 1
fi

echo "== presets =="
run mkdir -p "$PRESET_DIR" "$AUTOLOAD_DIR"
for preset in "$SPEAKERS_PRESET" "$HEADPHONES_PRESET"; do
  run install -m 0644 "$REPO_DIR/presets/$preset.json" "$PRESET_DIR/$preset.json"
  [[ "$DRY_RUN" == "1" ]] || echo "  -> $PRESET_DIR/$preset.json"
done

echo "== autoload (device routes) =="
if ! detection="$(python3 "$REPO_DIR/tools/detect_routes.py")"; then
  echo "warning: could not detect the speaker/headphone routes." >&2
  echo "         Set them by hand in EasyEffects > Output > Autoloading." >&2
else
  DEVICE_NAME=""; DEVICE_DESCRIPTION=""; SPEAKER_ROUTE=""; HEADPHONE_ROUTE=""
  while IFS='=' read -r key value; do
    case "$key" in
      DEVICE_NAME) DEVICE_NAME="$value" ;;
      DEVICE_DESCRIPTION) DEVICE_DESCRIPTION="$value" ;;
      SPEAKER_ROUTE) SPEAKER_ROUTE="$value" ;;
      HEADPHONE_ROUTE) HEADPHONE_ROUTE="$value" ;;
    esac
  done <<< "$detection"
  if [[ -z "$DEVICE_NAME" || -z "$SPEAKER_ROUTE" ]]; then
    echo "warning: incomplete route detection, skipping autoload" >&2
  else
    write_autoload "$DEVICE_NAME" "$DEVICE_DESCRIPTION" "$SPEAKER_ROUTE" "$SPEAKERS_PRESET"
    write_autoload "$DEVICE_NAME" "$DEVICE_DESCRIPTION" "$HEADPHONE_ROUTE" "$HEADPHONES_PRESET"
    echo "  device: $DEVICE_NAME"
  fi
fi

if [[ "$RESTART" == "1" && "$DRY_RUN" == "0" ]]; then
  echo "== restart EasyEffects =="
  if pgrep -x easyeffects >/dev/null 2>&1; then
    easyeffects -q || true
    for _ in $(seq 1 20); do
      pgrep -x easyeffects >/dev/null 2>&1 || break
      sleep 0.2
    done
  fi
  nohup setsid easyeffects >/dev/null 2>&1 &
  sleep 4
  echo "  loaded profile: $(easyeffects -s 2>/dev/null | tr -d '\n' | sed 's/.*output: //')"
else
  echo "== EasyEffects not restarted =="
  echo "  run 'easyeffects -q && easyeffects &' or replug the headphones to trigger autoload"
fi
