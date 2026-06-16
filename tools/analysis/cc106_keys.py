#!/usr/bin/env python3
"""CC 106/107 remote key press for OP-XY.

Simulates physical key presses on the OP-XY via MIDI:
  CC 106 = key down
  CC 107 = key up
Same value maps to the same key on both CCs.

Usage:
  python tools/cc106_keys.py list
  python tools/cc106_keys.py tap project              # down + up (default 0.5s hold)
  python tools/cc106_keys.py tap project --hold 0.1
  python tools/cc106_keys.py tap project m1 track3    # multiple taps in sequence
  python tools/cc106_keys.py down 26                  # key down only
  python tools/cc106_keys.py up 26                    # key up only
  python tools/cc106_keys.py run script.txt           # run a script file

Prerequisites:
  pip install mido python-rtmidi
"""

import argparse
import sys
import time
from pathlib import Path

try:
    import mido
except ImportError:
    print("ERROR: mido not installed. Run: pip install mido python-rtmidi", file=sys.stderr)
    sys.exit(1)

DEFAULT_PORT = "OP-XY"
CC_KEY_DOWN = 106
CC_KEY_UP = 107
DEFAULT_CHANNEL = 0  # MIDI channel 1

# ---------------------------------------------------------------------------
# Key name → CC value mapping
# ---------------------------------------------------------------------------

KEY_MAP = {
    # Mode / Navigation
    "project": 0,
    "tempo": 1,
    "instrument": 2,
    "aux": 3,
    "arranger": 4,
    "mixer": 5,
    "m1": 6,
    "m2": 7,
    "m3": 8,
    "m4": 9,
    # Tracks
    "track1": 14, "t1": 14,
    "track2": 15, "t2": 15,
    "track3": 16, "t3": 16,
    "track4": 17, "t4": 17,
    "track5": 18, "t5": 18,
    "track6": 19, "t6": 19,
    "track7": 20, "t7": 20,
    "track8": 21, "t8": 21,
    # Special
    "player": 22, "arp": 22,
    "sample": 23,
    "com": 24,
    "bar": 25,
    # Transport
    "record": 50, "rec": 50,
    "play": 51,
    "stop": 52,
    "minus": 53,
    "plus": 54,
    "shift": 55,
    # Sequencer steps
    "s1": 56, "step1": 56,
    "s2": 57, "step2": 57,
    "s3": 58, "step3": 58,
    "s4": 59, "step4": 59,
    "s5": 60, "step5": 60,
    "s6": 61, "step6": 61,
    "s7": 62, "step7": 62,
    "s8": 63, "step8": 63,
    "s9": 64, "step9": 64,
    "s10": 65, "step10": 65,
    "s11": 66, "step11": 66,
    "s12": 67, "step12": 67,
    "s13": 68, "step13": 68,
    "s14": 69, "step14": 69,
    "s15": 70, "step15": 70,
    "s16": 71, "step16": 71,
}

# Keyboard keys: F3 to E5 (24 keys, CC values 26-49)
_NOTE_NAMES = ["f", "f#", "g", "g#", "a", "a#", "b",
               "c", "c#", "d", "d#", "e"]
for _i in range(24):
    _cc_val = 26 + _i
    _octave = 3 + (_i + 5) // 12
    _note = _NOTE_NAMES[_i % 12]
    _name = f"{_note}{_octave}"
    KEY_MAP[f"key-{_name}"] = _cc_val
    KEY_MAP[_name] = _cc_val
    KEY_MAP[f"k{_i+1}"] = _cc_val

_FLAT_MAP = {"db": "c#", "eb": "d#", "gb": "f#", "ab": "g#", "bb": "a#"}
for _flat, _sharp in _FLAT_MAP.items():
    for _oct in range(3, 6):
        _sk = f"{_sharp}{_oct}"
        _fk = f"{_flat}{_oct}"
        if _sk in KEY_MAP:
            KEY_MAP[_fk] = KEY_MAP[_sk]
            KEY_MAP[f"key-{_fk}"] = KEY_MAP[_sk]


def resolve_key(name: str) -> int:
    """Resolve a key name or raw number to a CC value."""
    low = name.lower().strip()
    if low in KEY_MAP:
        return KEY_MAP[low]
    try:
        val = int(low)
        if 0 <= val <= 127:
            return val
        raise ValueError(f"CC value must be 0-127, got {val}")
    except ValueError:
        pass
    raise ValueError(
        f"Unknown key '{name}'. Use 'list' command to see available names."
    )


def key_label(name_or_val) -> str:
    """Human-readable label for a key."""
    low = str(name_or_val).lower().strip()
    if low in KEY_MAP:
        return low
    # Reverse lookup
    try:
        val = int(low)
        for k, v in KEY_MAP.items():
            if v == val and len(k) > 2:
                return k
    except ValueError:
        pass
    return str(name_or_val)


# ---------------------------------------------------------------------------
# MIDI helpers
# ---------------------------------------------------------------------------

def find_port(name: str, direction: str = "output") -> str:
    if direction == "output":
        ports = mido.get_output_names()
    else:
        ports = mido.get_input_names()
    if name in ports:
        return name
    matches = [p for p in ports if name.lower() in p.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(f"Ambiguous port '{name}': {matches}")
    raise RuntimeError(
        f"MIDI {direction} port '{name}' not found.\n"
        f"Available: {ports}\n"
        "Is the OP-XY connected?"
    )


def send_down(port, value: int, channel: int = DEFAULT_CHANNEL) -> None:
    """CC 106 = key down."""
    port.send(mido.Message("control_change", channel=channel,
                           control=CC_KEY_DOWN, value=value))


def send_up(port, value: int, channel: int = DEFAULT_CHANNEL) -> None:
    """CC 107 = key up."""
    port.send(mido.Message("control_change", channel=channel,
                           control=CC_KEY_UP, value=value))


def tap(port, value: int, hold: float = 0.5, channel: int = DEFAULT_CHANNEL) -> None:
    """Press and release a key with a hold duration."""
    send_down(port, value, channel)
    time.sleep(hold)
    send_up(port, value, channel)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(args) -> int:
    """List all known key names."""
    by_value = {}
    for name, val in sorted(KEY_MAP.items(), key=lambda x: (x[1], x[0])):
        by_value.setdefault(val, []).append(name)

    print(f"{'CC':>3}  Names")
    print(f"{'---':>3}  -----")
    for val in sorted(by_value):
        names = ", ".join(sorted(by_value[val], key=len))
        print(f"{val:3d}  {names}")
    return 0


def cmd_tap(args) -> int:
    """Tap (down + up) one or more keys."""
    port_name = find_port(args.port)
    out = mido.open_output(port_name)

    for i, key_name in enumerate(args.keys):
        value = resolve_key(key_name)
        label = key_label(key_name)
        hold = args.hold
        print(f"  tap {label} (CC {value}) hold={hold}s")
        tap(out, value, hold=hold, channel=args.channel)
        if i < len(args.keys) - 1:
            time.sleep(args.gap)

    out.close()
    return 0


def cmd_down(args) -> int:
    """Send key down only."""
    port_name = find_port(args.port)
    out = mido.open_output(port_name)
    value = resolve_key(args.key)
    label = key_label(args.key)
    print(f"  DOWN {label} (CC 106 = {value})")
    send_down(out, value, args.channel)
    out.close()
    return 0


def cmd_up(args) -> int:
    """Send key up only."""
    port_name = find_port(args.port)
    out = mido.open_output(port_name)
    value = resolve_key(args.key)
    label = key_label(args.key)
    print(f"  UP   {label} (CC 107 = {value})")
    send_up(out, value, args.channel)
    out.close()
    return 0


def cmd_run(args) -> int:
    """Run a script file.

    Script format (one command per line):
      tap project 0.5          # tap with hold duration
      tap m1 3.0               # long hold for new project
      down c4                  # key down only
      up c4                    # key up only
      wait 1.0                 # pause
      # comment
    """
    script_path = Path(args.script)
    if not script_path.exists():
        print(f"ERROR: {script_path} not found", file=sys.stderr)
        return 1

    port_name = find_port(args.port)
    out = mido.open_output(port_name)

    for lineno, raw_line in enumerate(script_path.read_text().splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        cmd = parts[0].lower()

        if cmd == "tap":
            key_name = parts[1]
            hold = float(parts[2]) if len(parts) > 2 else 0.5
            value = resolve_key(key_name)
            label = key_label(key_name)
            print(f"  [{lineno:3d}] tap {label} (CC {value}) hold={hold}s")
            tap(out, value, hold=hold, channel=args.channel)
        elif cmd == "down":
            key_name = parts[1]
            value = resolve_key(key_name)
            label = key_label(key_name)
            print(f"  [{lineno:3d}] DOWN {label} (CC 106 = {value})")
            send_down(out, value, args.channel)
        elif cmd == "up":
            key_name = parts[1]
            value = resolve_key(key_name)
            label = key_label(key_name)
            print(f"  [{lineno:3d}] UP   {label} (CC 107 = {value})")
            send_up(out, value, args.channel)
        elif cmd == "wait":
            duration = float(parts[1])
            print(f"  [{lineno:3d}] wait {duration}s")
            time.sleep(duration)
        else:
            print(f"  [{lineno:3d}] UNKNOWN: {line}", file=sys.stderr)

    out.close()
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cc106_keys.py",
        description="CC 106/107 remote key press for OP-XY (106=down, 107=up)",
    )
    p.add_argument("--port", default=DEFAULT_PORT,
                   help=f"MIDI port name (default: {DEFAULT_PORT})")
    p.add_argument("--channel", type=int, default=1,
                   help="MIDI channel 1-16 (default: 1)")

    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all key names and CC values")

    t = sub.add_parser("tap", help="Tap keys (down + hold + up)")
    t.add_argument("keys", nargs="+", help="Key names to tap")
    t.add_argument("--hold", type=float, default=0.5,
                   help="Hold duration in seconds (default: 0.5)")
    t.add_argument("--gap", type=float, default=0.5,
                   help="Gap between taps in seconds (default: 0.5)")

    d = sub.add_parser("down", help="Send key down (CC 106)")
    d.add_argument("key", help="Key name or CC value")

    u = sub.add_parser("up", help="Send key up (CC 107)")
    u.add_argument("key", help="Key name or CC value")

    r = sub.add_parser("run", help="Run a script file")
    r.add_argument("script", help="Path to script file")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.channel = max(0, min(15, args.channel - 1))

    dispatch = {
        "list": cmd_list,
        "tap": cmd_tap,
        "down": cmd_down,
        "up": cmd_up,
        "run": cmd_run,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except (RuntimeError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
