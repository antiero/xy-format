#!/usr/bin/env python3
"""Investigate whether body length is stored anywhere in the .xy format."""

import sys, struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from xy.container import XYProject

CORPUS = Path("src/one-off-changes-from-default")
OUTPUT = Path("output/multistep")

def load(path):
    data = Path(path).read_bytes()
    proj = XYProject.from_bytes(data)
    return data, proj

def hexdump(data, offset=0, width=16):
    """Pretty hex dump with offsets."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hexpart = ' '.join(f'{b:02x}' for b in chunk)
        ascpart = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'  {offset+i:04x}: {hexpart:<{width*3}}  {ascpart}')
    return '\n'.join(lines)

def find_u16_le(data, target):
    """Find all offsets where u16 LE == target."""
    needle = struct.pack('<H', target)
    results = []
    for i in range(len(data) - 1):
        if data[i:i+2] == needle:
            results.append(i)
    return results

def find_u32_le(data, target):
    """Find all offsets where u32 LE == target."""
    needle = struct.pack('<I', target)
    results = []
    for i in range(len(data) - 3):
        if data[i:i+4] == needle:
            results.append(i)
    return results

# ============================================================
print("=" * 70)
print("SECTION 1: Track Block Header Analysis (118, 118b, 119)")
print("=" * 70)
print()

for name in ["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"]:
    path = CORPUS / name
    data, proj = load(path)
    t1 = proj.tracks[0]
    body = t1.body
    
    print(f"--- {name} ---")
    print(f"  Track 1 body size: {len(body)}")
    print(f"  Track 1 preamble:  {t1.preamble.hex()}")
    print(f"  Track 1 type_byte: {hex(t1.type_byte)}")
    
    # Body starts with signature (8 bytes), then type_byte at +8, then more header
    # Show the first 32 bytes of body (header region)
    print(f"  Body header (first 48 bytes):")
    print(hexdump(body[:48]))
    
    # Parse known header fields
    sig = body[0:8]
    type_b = body[8]
    print(f"  Parsed: sig={sig.hex()}, type=0x{type_b:02x}")
    print(f"  body[9:16] = {body[9:16].hex()}")
    
    # Check for any u16/u32 in the header that match body size
    body_size = len(body)
    print(f"  Searching body header (first 64 bytes) for u16={body_size}...")
    for off in range(min(64, len(body)) - 1):
        val16 = struct.unpack_from('<H', body, off)[0]
        if val16 == body_size:
            print(f"    MATCH u16 at body offset {off}: {val16}")
    for off in range(min(64, len(body)) - 3):
        val32 = struct.unpack_from('<I', body, off)[0]
        if val32 == body_size:
            print(f"    MATCH u32 at body offset {off}: {val32}")
    print()

# ============================================================
print("=" * 70)
print("SECTION 2: Preamble Analysis")
print("=" * 70)
print()

for name in ["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"]:
    path = CORPUS / name
    _, proj = load(path)
    t1 = proj.tracks[0]
    pre = t1.preamble
    body_size = len(t1.body)
    
    print(f"--- {name} ---")
    print(f"  Preamble bytes: {pre.hex()} = {list(pre)}")
    print(f"  Preamble as u32 LE: {struct.unpack('<I', pre)[0]}")
    print(f"  Preamble as u16 LE pair: {struct.unpack('<HH', pre)}")
    print(f"  Body size: {body_size}")
    print(f"  Body size matches any preamble component? u16={body_size in struct.unpack('<HH', pre)}, u32={struct.unpack('<I', pre)[0] == body_size}")
    print()

# ============================================================
print("=" * 70)
print("SECTION 3: Pre-Track Region Scan")
print("=" * 70)
print()

for name in ["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"]:
    path = CORPUS / name
    data, proj = load(path)
    t1 = proj.tracks[0]
    pre_track = proj.pre_track
    body_size = len(t1.body)
    block_size = 4 + body_size  # preamble + body
    
    print(f"--- {name} ---")
    print(f"  Body size: {body_size}, Block size: {block_size}")
    
    # Search pre-track for u16 LE matches
    targets = [body_size, block_size, body_size - 8]  # body, block, body minus sig
    for target in targets:
        if target < 0 or target > 65535:
            continue
        matches = find_u16_le(pre_track, target)
        if matches:
            print(f"  u16 LE matches for {target}: offsets {[f'0x{o:02x}' for o in matches]}")
        else:
            print(f"  u16 LE matches for {target}: NONE")
    
    # Also check u32
    for target in [body_size, block_size]:
        matches = find_u32_le(pre_track, target)
        if matches:
            print(f"  u32 LE matches for {target}: offsets {[f'0x{o:02x}' for o in matches]}")
    print()

# Show pre-track hex dump for comparison
print("Pre-track hex comparison:")
for name in ["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"]:
    path = CORPUS / name
    data, proj = load(path)
    print(f"\n  --- {name} pre-track ({len(proj.pre_track)} bytes) ---")
    print(hexdump(proj.pre_track))

# ============================================================
print("\n" + "=" * 70)
print("SECTION 4: Handle Table Check")
print("=" * 70)
print()

for name in ["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"]:
    path = CORPUS / name
    data, proj = load(path)
    pt = proj.pre_track
    
    print(f"--- {name} ---")
    # Handle table at 0x58-0x7B (9 entries of 4 bytes each = 36 bytes)
    print(f"  Handle table (0x58-0x7B):")
    for i in range(9):
        off = 0x58 + i * 4
        val = struct.unpack_from('<I', pt, off)[0]
        print(f"    Handle[{i}] @ 0x{off:02x}: {val} (0x{val:08x})")
    print()

# Diff the handle tables
print("Handle table differences between files:")
handles = {}
for name in ["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"]:
    path = CORPUS / name
    _, proj = load(path)
    pt = proj.pre_track
    handles[name] = [struct.unpack_from('<I', pt, 0x58 + i*4)[0] for i in range(9)]

for i in range(9):
    vals = [handles[n][i] for n in ["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"]]
    if len(set(vals)) > 1:
        print(f"  Handle[{i}] DIFFERS: 118={vals[0]}, 118b={vals[1]}, 119={vals[2]}")
    else:
        print(f"  Handle[{i}] same across all: {vals[0]}")

# ============================================================
print("\n" + "=" * 70)
print("SECTION 5: Cross-File Body Size Encoding Search")
print("=" * 70)
print()

# Pick 10 diverse files
corpus_files = sorted(CORPUS.glob("unnamed *.xy"))
# Get body sizes to pick diverse ones
file_sizes = []
for f in corpus_files:
    try:
        _, p = load(f)
        file_sizes.append((f, len(p.tracks[0].body)))
    except:
        pass

# Sort by body size, pick every Nth for diversity
file_sizes.sort(key=lambda x: x[1])
step = max(1, len(file_sizes) // 10)
selected = file_sizes[::step][:10]

print(f"Selected {len(selected)} files with diverse T1 body sizes:\n")
for fpath, bsize in selected:
    print(f"  {fpath.name}: T1 body={bsize}")
print()

for fpath, body_size in selected:
    raw_data, proj = load(fpath)
    pre_track = proj.pre_track
    
    # Search in pre-track region
    u16_pre = find_u16_le(pre_track, body_size)
    u32_pre = find_u32_le(pre_track, body_size)
    
    # Search in all track headers (first 64 bytes of each body)
    header_matches = []
    for ti, track in enumerate(proj.tracks):
        tbody = track.body
        for off in range(min(64, len(tbody)) - 1):
            val16 = struct.unpack_from('<H', tbody, off)[0]
            if val16 == body_size:
                header_matches.append(f"T{ti+1} body[{off}] u16")
        for off in range(min(64, len(tbody)) - 3):
            val32 = struct.unpack_from('<I', tbody, off)[0]
            if val32 == body_size:
                header_matches.append(f"T{ti+1} body[{off}] u32")
    
    # Search in preambles
    preamble_matches = []
    for ti, track in enumerate(proj.tracks):
        pre = track.preamble
        if len(pre) >= 2:
            for off in range(len(pre) - 1):
                val16 = struct.unpack_from('<H', pre, off)[0]
                if val16 == body_size:
                    preamble_matches.append(f"T{ti+1} preamble[{off}] u16")
    
    status = "NO MATCHES"
    details = []
    if u16_pre:
        details.append(f"pre-track u16 @ {[f'0x{o:02x}' for o in u16_pre]}")
    if u32_pre:
        details.append(f"pre-track u32 @ {[f'0x{o:02x}' for o in u32_pre]}")
    if header_matches:
        details.append(f"headers: {header_matches}")
    if preamble_matches:
        details.append(f"preambles: {preamble_matches}")
    if details:
        status = "; ".join(details)
    
    print(f"  {fpath.name} (T1 body={body_size}): {status}")

# Also search for body sizes of ALL 16 tracks in a single file
print("\n  --- Full search: ALL track body sizes in unnamed 118 ---")
raw_data, proj = load(CORPUS / "unnamed 118.xy")
for ti, track in enumerate(proj.tracks):
    bsize = len(track.body)
    # Search entire raw file
    u16_all = find_u16_le(raw_data, bsize)
    u32_all = find_u32_le(raw_data, bsize)
    if u16_all or u32_all:
        print(f"  T{ti+1} body={bsize}: u16@{[f'0x{o:04x}' for o in u16_all]}, u32@{[f'0x{o:04x}' for o in u32_all]}")
    else:
        print(f"  T{ti+1} body={bsize}: no encoding found anywhere in file")

# ============================================================
print("\n" + "=" * 70)
print("SECTION 6: v6a vs v6b Comparison")
print("=" * 70)
print()

test_files = {
    "v6a (works)": OUTPUT / "v6a_119_to_all_hold.xy",
    "v6b (crashes)": OUTPUT / "v6b_119_to_118b_pattern.xy",
    "unnamed 118": CORPUS / "unnamed 118.xy",
    "unnamed 118b": CORPUS / "unnamed 118b.xy",
    "unnamed 119": CORPUS / "unnamed 119.xy",
}

for label, path in test_files.items():
    if not path.exists():
        print(f"--- {label}: FILE NOT FOUND ---")
        continue
    raw_data, proj = load(path)
    t1 = proj.tracks[0]
    
    print(f"--- {label} ({path.name}) ---")
    print(f"  File size: {len(raw_data)}")
    print(f"  T1 body size: {len(t1.body)}")
    print(f"  T1 preamble:  {t1.preamble.hex()} = {list(t1.preamble)}")
    print(f"  T1 type_byte:  {hex(t1.type_byte)}")
    print(f"  T1 body[:32]:  {t1.body[:32].hex()}")
    print(f"  T1 body[-32:]: {t1.body[-32:].hex()}")
    
    # Show handle table
    pt = proj.pre_track
    handles = [struct.unpack_from('<I', pt, 0x58 + i*4)[0] for i in range(9)]
    print(f"  Handles: {handles}")
    
    # Show all track preambles and body sizes
    print(f"  All tracks:")
    for ti, track in enumerate(proj.tracks):
        print(f"    T{ti+1:2d}: preamble={track.preamble.hex()}, body={len(track.body)}, type=0x{track.type_byte:02x}")
    print()

# Direct byte comparison between v6a and v6b
print("=" * 70)
print("DIRECT BYTE COMPARISON: v6a vs v6b")
print("=" * 70)
v6a_path = OUTPUT / "v6a_119_to_all_hold.xy"
v6b_path = OUTPUT / "v6b_119_to_118b_pattern.xy"
if v6a_path.exists() and v6b_path.exists():
    v6a_data = v6a_path.read_bytes()
    v6b_data = v6b_path.read_bytes()
    print(f"  v6a size: {len(v6a_data)}")
    print(f"  v6b size: {len(v6b_data)}")
    
    if len(v6a_data) == len(v6b_data):
        diffs = []
        for i in range(len(v6a_data)):
            if v6a_data[i] != v6b_data[i]:
                diffs.append(i)
        print(f"  Same size, {len(diffs)} byte differences")
        if len(diffs) <= 50:
            for off in diffs:
                print(f"    offset 0x{off:04x}: v6a=0x{v6a_data[off]:02x}, v6b=0x{v6b_data[off]:02x}")
        else:
            print(f"  First 20 diffs:")
            for off in diffs[:20]:
                print(f"    offset 0x{off:04x}: v6a=0x{v6a_data[off]:02x}, v6b=0x{v6b_data[off]:02x}")
            print(f"  Last 10 diffs:")
            for off in diffs[-10:]:
                print(f"    offset 0x{off:04x}: v6a=0x{v6a_data[off]:02x}, v6b=0x{v6b_data[off]:02x}")
    else:
        print(f"  DIFFERENT SIZES! Diff = {len(v6b_data) - len(v6a_data)} bytes")
        # Find first difference
        min_len = min(len(v6a_data), len(v6b_data))
        for i in range(min_len):
            if v6a_data[i] != v6b_data[i]:
                print(f"  First diff at offset 0x{i:04x}: v6a=0x{v6a_data[i]:02x}, v6b=0x{v6b_data[i]:02x}")
                break
else:
    print("  One or both files not found")

print("\n" + "=" * 70)
print("SUMMARY / CONCLUSIONS")
print("=" * 70)
print()
print("If no body-size encoding was found in pre-track, preambles, or headers,")
print("then the format does NOT store body length fields that need updating.")
print("The firmware likely determines body boundaries by parsing the content itself")
print("(using sentinels, type bytes, or structure-based parsing).")
