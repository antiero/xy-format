#!/usr/bin/env python3
"""CC 86 project select test for OP-XY.

Uploads .xy files with 3-digit prefixes (000, 001, ...) to the device,
then uses MIDI CC 86 to select them by index.  The OP-XY maps CC 86
value N to the project whose name starts with that 3-digit prefix.

Two modes:
  single   — upload one file, select it via CC 86, verify via clock
  batch    — upload multiple files, test each sequentially

The clock monitor detects pass/crash: if MIDI clock ticks arrive after
sending Start, the project loaded successfully.  No clock = crash.

MIDI is sent/received via an external USB MIDI adapter connected to the
OP-XY's AUX Type A MIDI port (the USB-C port is power only in this setup).
The adapter appears as "USB MIDI Interface" on macOS.

Prerequisites:
  pip install mido python-rtmidi

Usage:
  python tools/cc86_select.py list-ports
  python tools/cc86_select.py select 0
  python tools/cc86_select.py select 5 --start --clock-timeout 3
  python tools/cc86_select.py test output/test_note.xy --slot 0
  python tools/cc86_select.py test output/test_note.xy output/gate_test.xy --start
"""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from typing import List, Optional

try:
    import mido
except ImportError:
    print("ERROR: mido not installed. Run: pip install mido python-rtmidi", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.mtp_upload import (
    MTPError,
    auto_detect_client,
    find_fieldkit_mount,
    FieldKitClient,
)

DEFAULT_PORT = "USB MIDI Interface"
CC_PROJECT_SELECT = 86
DEFAULT_CHANNEL = 0  # MIDI channel 1 (0-indexed)


# ---------------------------------------------------------------------------
# MIDI helpers
# ---------------------------------------------------------------------------

def find_port(name: str, direction: str = "output") -> str:
    """Find a MIDI port matching name (substring match)."""
    if direction == "output":
        ports = mido.get_output_names()
    else:
        ports = mido.get_input_names()
    # Exact match first
    if name in ports:
        return name
    # Substring match
    matches = [p for p in ports if name.lower() in p.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(f"Ambiguous port '{name}': {matches}")
    raise RuntimeError(
        f"MIDI {direction} port '{name}' not found.\n"
        f"Available: {ports}\n"
        "Is the OP-XY connected and NOT in MTP mode?"
    )


def send_cc86(port: mido.ports.BaseOutput, value: int, channel: int = DEFAULT_CHANNEL) -> None:
    """Send CC 86 to select a project by index."""
    msg = mido.Message("control_change", channel=channel, control=CC_PROJECT_SELECT, value=value)
    port.send(msg)


def send_start(port: mido.ports.BaseOutput) -> None:
    """Send MIDI Start to trigger playback."""
    port.send(mido.Message("start"))


def send_stop(port: mido.ports.BaseOutput) -> None:
    """Send MIDI Stop and All Notes Off."""
    for ch in range(16):
        port.send(mido.Message("control_change", channel=ch, control=123, value=0))
    port.send(mido.Message("stop"))


def wait_for_clock(
    in_port: mido.ports.BaseInput,
    timeout: float = 3.0,
    min_ticks: int = 6,
) -> bool:
    """Wait for MIDI clock ticks.  Returns True if enough ticks arrive.

    min_ticks=6 means ~1/4 beat at 24 PPQN — enough to confirm playback.
    """
    ticks = 0
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msg = in_port.poll()
        if msg is None:
            time.sleep(0.01)
            continue
        if msg.type == "clock":
            ticks += 1
            if ticks >= min_ticks:
                return True
    return False


def drain_input(in_port: mido.ports.BaseInput) -> None:
    """Drain any pending messages from the input port."""
    while in_port.poll() is not None:
        pass


# ---------------------------------------------------------------------------
# File naming
# ---------------------------------------------------------------------------

def prefixed_name(slot: int, original_name: str) -> str:
    """Generate a 3-digit prefixed filename for CC 86 addressing.

    slot=0, name="test.xy" → "000test.xy"
    slot=5, name="my file.xy" → "005my file.xy"
    """
    if slot < 0 or slot > 127:
        raise ValueError(f"Slot must be 0-127, got {slot}")
    return f"{slot:03d}{original_name}"


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_list_ports(args) -> int:
    """Print available MIDI ports."""
    out_ports = mido.get_output_names()
    in_ports = mido.get_input_names()
    print("MIDI output ports:")
    for p in out_ports:
        marker = " ← " if "op-xy" in p.lower() else "   "
        print(f"  {marker}{p}")
    print("\nMIDI input ports:")
    for p in in_ports:
        marker = " ← " if "op-xy" in p.lower() else "   "
        print(f"  {marker}{p}")
    if not out_ports and not in_ports:
        print("\nNo MIDI ports found. Is the OP-XY connected?")
    return 0


def cmd_select(args) -> int:
    """Send CC 86 to select a project by index."""
    port_name = find_port(args.port)
    value = args.value

    out = mido.open_output(port_name)
    print(f"Sending CC 86 = {value} on channel {args.channel + 1} → {port_name}")
    send_cc86(out, value, args.channel)

    if args.start:
        time.sleep(args.load_wait)
        print(f"Sending MIDI Start (waited {args.load_wait}s for project load)...")
        send_start(out)

        if args.clock_timeout > 0:
            try:
                in_name = find_port(args.port, "input")
                in_port = mido.open_input(in_name)
                drain_input(in_port)
                print(f"Monitoring clock for {args.clock_timeout}s...")
                got_clock = wait_for_clock(in_port, timeout=args.clock_timeout)
                in_port.close()
                if got_clock:
                    print("PASS — clock ticks received (project loaded)")
                else:
                    print("FAIL — no clock (project may have crashed)")
                send_stop(out)
                out.close()
                return 0 if got_clock else 1
            except RuntimeError:
                print("(no input port for clock monitoring)")

        # No clock monitoring — just wait a bit and stop
        time.sleep(2.0)
        send_stop(out)

    out.close()
    return 0


def cmd_test(args) -> int:
    """Upload files with prefixed names and test via CC 86."""
    files = [Path(f) for f in args.files]
    for f in files:
        if not f.exists():
            print(f"ERROR: {f} not found", file=sys.stderr)
            return 1

    start_slot = args.slot

    # Connect to device for file operations
    try:
        client = auto_detect_client(verbose=args.verbose)
    except MTPError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Phase 1: Upload files with prefixed names
    print(f"Uploading {len(files)} file(s) to device with 3-digit prefixes...")
    uploaded_names: List[str] = []
    for i, f in enumerate(files):
        slot = start_slot + i
        pname = prefixed_name(slot, f.name)
        # Copy to temp with prefixed name, then upload
        tmp = Path(f"/tmp/{pname}")
        shutil.copy2(str(f), str(tmp))
        try:
            client.put(str(tmp), "/projects/")
            uploaded_names.append(pname)
            print(f"  [{slot:3d}] {pname}")
        except MTPError as exc:
            print(f"  FAIL {pname}: {exc}", file=sys.stderr)
        finally:
            tmp.unlink(missing_ok=True)

    if not uploaded_names:
        print("ERROR: no files uploaded", file=sys.stderr)
        return 1

    if not args.start:
        print(f"\nUploaded {len(uploaded_names)} file(s). Exit MTP mode to test with CC 86.")
        print("Re-run with --start to also send CC 86 + verify clock.")
        return 0

    # Phase 2: Exit MTP mode required for MIDI
    print(f"\n{'='*60}")
    print("Files uploaded. Exit MTP mode on the OP-XY now.")
    print("  (Press any key on the device, or power cycle)")
    print(f"{'='*60}")
    input("Press Enter here once OP-XY is out of MTP mode...")

    # Phase 3: Send CC 86 for each file and monitor clock
    port_name = find_port(args.port)
    out = mido.open_output(port_name)

    in_port = None
    if args.clock_timeout > 0:
        try:
            in_name = find_port(args.port, "input")
            in_port = mido.open_input(in_name)
        except RuntimeError:
            print("WARNING: no input port for clock monitoring", file=sys.stderr)

    results = []
    for i, pname in enumerate(uploaded_names):
        slot = start_slot + i
        print(f"\n--- Testing slot {slot}: {pname} ---")

        send_cc86(out, slot, args.channel)
        time.sleep(args.load_wait)

        if args.start:
            send_start(out)

            if in_port:
                drain_input(in_port)
                got_clock = wait_for_clock(in_port, timeout=args.clock_timeout)
                status = "PASS" if got_clock else "CRASH"
                print(f"  {status}")
                results.append((slot, pname, status))
                send_stop(out)

                if not got_clock:
                    # Crash detected — device needs recovery
                    print("  Crash detected. Waiting for device recovery...")
                    time.sleep(args.crash_recovery)
            else:
                time.sleep(2.0)
                send_stop(out)
                results.append((slot, pname, "UNKNOWN"))

        time.sleep(0.5)

    # Summary
    if in_port:
        in_port.close()
    out.close()

    print(f"\n{'='*60}")
    print("Results:")
    for slot, name, status in results:
        print(f"  [{slot:3d}] {status:5s}  {name}")
    passes = sum(1 for _, _, s in results if s == "PASS")
    crashes = sum(1 for _, _, s in results if s == "CRASH")
    print(f"\n{passes} pass, {crashes} crash, {len(results) - passes - crashes} unknown")

    # Phase 4: Cleanup uploaded files
    if args.cleanup:
        print("\nCleaning up uploaded files...")
        try:
            cleanup_client = auto_detect_client(verbose=args.verbose)
            for pname in uploaded_names:
                try:
                    cleanup_client.rm(f"/projects/{pname}")
                    print(f"  OK {pname}")
                except MTPError:
                    print(f"  SKIP {pname} (device may need MTP mode)")
        except MTPError:
            print("  (cleanup skipped — device not in MTP mode)")

    return 1 if crashes > 0 else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cc86_select.py",
        description="CC 86 project select test for OP-XY",
    )
    p.add_argument("--port", default=DEFAULT_PORT,
                   help=f"MIDI port name (default: {DEFAULT_PORT})")
    p.add_argument("--channel", type=int, default=1,
                   help="MIDI channel 1-16 (default: 1)")
    p.add_argument("--verbose", "-v", action="store_true")

    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list-ports", help="List available MIDI ports")

    sel = sub.add_parser("select", help="Send CC 86 to select a project")
    sel.add_argument("value", type=int, help="CC 86 value (0-127)")
    sel.add_argument("--start", action="store_true",
                     help="Also send MIDI Start and monitor clock")
    sel.add_argument("--load-wait", type=float, default=0.5,
                     help="Seconds to wait after CC 86 before Start (default: 0.5)")
    sel.add_argument("--clock-timeout", type=float, default=3.0,
                     help="Seconds to wait for clock ticks (default: 3.0)")

    test = sub.add_parser("test", help="Upload files and test via CC 86")
    test.add_argument("files", nargs="+", help=".xy files to test")
    test.add_argument("--slot", type=int, default=0,
                      help="Starting CC 86 slot (default: 0)")
    test.add_argument("--start", action="store_true",
                      help="Send MIDI Start and monitor clock after select")
    test.add_argument("--load-wait", type=float, default=0.5,
                      help="Seconds to wait for project load (default: 0.5)")
    test.add_argument("--clock-timeout", type=float, default=3.0,
                      help="Seconds to wait for clock (default: 3.0)")
    test.add_argument("--crash-recovery", type=float, default=20.0,
                      help="Seconds to wait after crash for recovery (default: 20)")
    test.add_argument("--cleanup", action="store_true",
                      help="Delete uploaded files after testing")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    # Convert 1-based channel to 0-based
    args.channel = max(0, min(15, args.channel - 1))

    dispatch = {
        "list-ports": cmd_list_ports,
        "select": cmd_select,
        "test": cmd_test,
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
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
