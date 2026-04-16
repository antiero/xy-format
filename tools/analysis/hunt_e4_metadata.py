"""Hunt for per-step metadata in Track 1 bodies that correlates with E4 block content."""
import sys
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from xy.container import XYProject

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from verify_sep_formula import parse_block_known


def load_track1(fname):
    """Load Track 1 body from an .xy file."""
    path = Path(__file__).resolve().parent.parent / 'src' / 'one-off-changes-from-default' / fname
    data = path.read_bytes()
    p = XYProject.from_bytes(data)
    return p.tracks[0]


def hex_dump(data, offset=0, width=16):
    """Pretty hex dump with offset labels."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'  {offset+i:04x}: {hex_part:<{width*3-1}}  |{ascii_part}|')
    return '\n'.join(lines)


def side_by_side_hex(datas, labels, start_offset=0, width=16):
    """Side-by-side hex dump of multiple byte sequences."""
    max_len = max(len(d) for d in datas)
    lines = []
    for i in range(0, max_len, width):
        for j, (data, label) in enumerate(zip(datas, labels)):
            chunk = data[i:i+width] if i < len(data) else b''
            hex_part = ' '.join(f'{b:02x}' for b in chunk)
            if j == 0:
                lines.append(f'  {start_offset+i:04x}: [{label:6s}] {hex_part}')
            else:
                # Highlight diffs against first
                ref_chunk = datas[0][i:i+width] if i < len(datas[0]) else b''
                markers = []
                for k, b in enumerate(chunk):
                    if k < len(ref_chunk) and b != ref_chunk[k]:
                        markers.append(f'\033[1;31m{b:02x}\033[0m')
                    else:
                        markers.append(f'{b:02x}')
                hex_part_marked = ' '.join(markers)
                lines.append(f'        [{label:6s}] {hex_part_marked}')
        lines.append('')
    return '\n'.join(lines)


def find_e4_block(body):
    """Find E4 block start and end offsets, plus parsed records."""
    e4_pos = None
    for i in range(0xA0, len(body)):
        if body[i] == 0xE4:
            e4_pos = i
            break
    if e4_pos is None:
        return None, None, None, None
    recs, seps = parse_block_known(body, e4_pos)
    total = 1  # E4 byte
    for idx, (type_id, size, rec) in enumerate(recs):
        total += size
        if idx < len(seps):
            total += 1
    e4_end = e4_pos + total
    return e4_pos, e4_end, recs, seps


def main():
    files = {
        '118': 'unnamed 118.xy',
        '118b': 'unnamed 118b.xy',
        '119': 'unnamed 119.xy',
    }

    tracks = {}
    bodies = {}
    e4_info = {}

    for key, fname in files.items():
        t1 = load_track1(fname)
        tracks[key] = t1
        bodies[key] = t1.body
        e4_start, e4_end, recs, seps = find_e4_block(t1.body)
        e4_info[key] = {
            'start': e4_start, 'end': e4_end,
            'recs': recs, 'seps': seps, 'size': e4_end - e4_start
        }

    keys = list(files.keys())

    # Summary
    print("=" * 80)
    print("TRACK 1 BODY METADATA HUNT")
    print("=" * 80)
    for key in keys:
        body = bodies[key]
        ei = e4_info[key]
        print(f"  {key:5s}: body_len={len(body)}, type={hex(tracks[key].type_byte)}, "
              f"E4=[{hex(ei['start'])}:{hex(ei['end'])}] ({ei['size']}B)")
    print()

    # =========================================================================
    # SECTION 1: Body header region body[0x00:0x24]
    # =========================================================================
    print("=" * 80)
    print("SECTION 1: Body header region (body[0x00:0x24])")
    print("=" * 80)
    region_start, region_end = 0x00, 0x24
    datas = [bodies[k][region_start:region_end] for k in keys]
    print(side_by_side_hex(datas, keys, start_offset=region_start))

    # =========================================================================
    # SECTION 2: Pre-E4 gap (body[0xA0:0xB1])
    # =========================================================================
    print("=" * 80)
    print("SECTION 2: Pre-E4 gap (body[0xA0:0xB2])")
    print("=" * 80)
    region_start, region_end = 0xA0, 0xB2
    datas = [bodies[k][region_start:region_end] for k in keys]
    print(side_by_side_hex(datas, keys, start_offset=region_start))

    # =========================================================================
    # SECTION 3: Post-E4 and secondary sentinel region
    # =========================================================================
    print("=" * 80)
    print("SECTION 3: Post-E4 block + secondary sentinel region")
    print("=" * 80)
    for key in keys:
        ei = e4_info[key]
        post_start = ei['end']
        post_end = min(post_start + 0x30, len(bodies[key]))
        print(f"  --- {key} (E4 ends at {hex(post_start)}, showing {hex(post_start)}:{hex(post_end)}) ---")
        print(hex_dump(bodies[key][post_start:post_end], offset=post_start))
        print()

    # =========================================================================
    # SECTION 4: Full body diff 118 vs 119 OUTSIDE E4 block
    # =========================================================================
    print("=" * 80)
    print("SECTION 4: Full body diff 118 vs 119 (EXCLUDING E4 block)")
    print("=" * 80)

    body_a, body_b = bodies['118'], bodies['119']
    ei_a, ei_b = e4_info['118'], e4_info['119']

    # E4 blocks may differ in size, so we need to align before/after
    diffs = []

    # Region before E4
    pre_len = min(ei_a['start'], ei_b['start'])
    for i in range(pre_len):
        if body_a[i] != body_b[i]:
            diffs.append((i, body_a[i], body_b[i], 'pre-E4'))

    # Region after E4 (align from end of body)
    post_a = body_a[ei_a['end']:]
    post_b = body_b[ei_b['end']:]
    post_len = min(len(post_a), len(post_b))
    for i in range(post_len):
        off_a = ei_a['end'] + i
        off_b = ei_b['end'] + i
        if post_a[i] != post_b[i]:
            diffs.append((off_a, post_a[i], post_b[i], f'post-E4 (118@{hex(off_a)}, 119@{hex(off_b)})'))

    # Also check for length diff in post region
    if len(post_a) != len(post_b):
        diffs.append((-1, len(post_a), len(post_b), f'LENGTH DIFF: post-E4 118={len(post_a)}B, 119={len(post_b)}B'))

    print(f"  Total differences outside E4 block: {len(diffs)}")
    for i, (pos, va, vb, region) in enumerate(diffs[:50]):
        if pos == -1:
            print(f"  [{i:3d}] {region}")
        else:
            ctx_a = body_a[max(0,pos-2):pos+3].hex(' ') if pos >= 0 else ''
            print(f"  [{i:3d}] body[{hex(pos):>6s}]: 118={hex(va):>4s}  119={hex(vb):>4s}  ({region})  ctx_118: {ctx_a}")
    print()

    # Also show the E4 block content diff for reference
    print("  --- E4 block sizes: 118={}, 119={} ---".format(ei_a['size'], ei_b['size']))
    e4_a = body_a[ei_a['start']:ei_a['end']]
    e4_b = body_b[ei_b['start']:ei_b['end']]
    e4_diffs = 0
    for i in range(min(len(e4_a), len(e4_b))):
        if e4_a[i] != e4_b[i]:
            e4_diffs += 1
    print(f"  E4 block internal diffs: {e4_diffs} bytes (+ {abs(len(e4_a)-len(e4_b))} size diff)")
    print()

    # =========================================================================
    # SECTION 5: Full body diff 118 vs 118b OUTSIDE E4 block
    # =========================================================================
    print("=" * 80)
    print("SECTION 5: Full body diff 118 vs 118b (EXCLUDING E4 block)")
    print("=" * 80)

    body_a, body_b = bodies['118'], bodies['118b']
    ei_a, ei_b = e4_info['118'], e4_info['118b']

    diffs = []

    # Region before E4
    pre_len = min(ei_a['start'], ei_b['start'])
    for i in range(pre_len):
        if body_a[i] != body_b[i]:
            diffs.append((i, body_a[i], body_b[i], 'pre-E4'))

    # Region after E4
    post_a = body_a[ei_a['end']:]
    post_b = body_b[ei_b['end']:]
    post_len = min(len(post_a), len(post_b))
    for i in range(post_len):
        off_a = ei_a['end'] + i
        off_b = ei_b['end'] + i
        if post_a[i] != post_b[i]:
            diffs.append((off_a, post_a[i], post_b[i], f'post-E4 (118@{hex(off_a)}, 118b@{hex(off_b)})'))

    if len(post_a) != len(post_b):
        diffs.append((-1, len(post_a), len(post_b), f'LENGTH DIFF: post-E4 118={len(post_a)}B, 118b={len(post_b)}B'))

    print(f"  Total differences outside E4 block: {len(diffs)}")
    for i, (pos, va, vb, region) in enumerate(diffs[:50]):
        if pos == -1:
            print(f"  [{i:3d}] {region}")
        else:
            ctx_a = body_a[max(0,pos-2):pos+3].hex(' ') if pos >= 0 else ''
            print(f"  [{i:3d}] body[{hex(pos):>6s}]: 118={hex(va):>4s}  118b={hex(vb):>4s}  ({region})  ctx_118: {ctx_a}")
    print()

    # Also show E4 block content diff
    print("  --- E4 block sizes: 118={}, 118b={} ---".format(ei_a['size'], ei_b['size']))
    e4_a = body_a[ei_a['start']:ei_a['end']]
    e4_b = body_b[ei_b['start']:ei_b['end']]
    e4_diffs = 0
    for i in range(min(len(e4_a), len(e4_b))):
        if e4_a[i] != e4_b[i]:
            e4_diffs += 1
    print(f"  E4 block internal diffs: {e4_diffs} bytes (+ {abs(len(e4_a)-len(e4_b))} size diff)")
    print()

    # =========================================================================
    # SECTION 6: Header mask words at body[0xAA:0xB1]
    # =========================================================================
    print("=" * 80)
    print("SECTION 6: Header mask words (block+0xB4 = body[0xAA] for type-07)")
    print("=" * 80)
    print("  Per step_component_notes.md, the header mask words at block+0xB4..0xBA")
    print("  map to body[0xAA..0xB0] for type-07 bodies (block starts at body-0x0A).")
    print()
    for key in keys:
        body = bodies[key]
        # block+0xB4 = body[0xAA] (since block+0x0A = body[0x00] for type-07: 
        # block offset = body offset + 0x0A, so body offset = block offset - 0x0A)
        # block+0xB4 -> body[0xB4-0x0A] = body[0xAA]
        w1 = struct.unpack_from('<H', body, 0xAA)[0]  # block+0xB4
        w2 = struct.unpack_from('<H', body, 0xAC)[0]  # block+0xB6
        w3 = struct.unpack_from('<H', body, 0xAE)[0]  # block+0xB8
        w4 = struct.unpack_from('<H', body, 0xB0)[0]  # block+0xBA
        print(f"  {key:5s}: block+0xB4={w1:#06x}  block+0xB6={w2:#06x}  "
              f"block+0xB8={w3:#06x}  block+0xBA={w4:#06x}")
        # Also show the raw bytes in wider context
        print(f"         body[0xA8:0xB2] = {body[0xA8:0xB2].hex(' ')}")
    print()

    # Bonus: Show the full sentinel table region for context
    print("  --- Extended sentinel/mask region body[0x48:0xB2] ---")
    for key in keys:
        body = bodies[key]
        print(f"\n  {key}:")
        print(hex_dump(body[0x48:0xB2], offset=0x48))

    # =========================================================================
    # SECTION 7: Allocation byte / per-step bitmask hunt
    # =========================================================================
    print()
    print("=" * 80)
    print("SECTION 7: Per-step bitmask region (body[0x48:0xA0])")
    print("Compare step activation masks across all 3 files")
    print("=" * 80)
    datas = [bodies[k][0x48:0xA0] for k in keys]
    print(side_by_side_hex(datas, keys, start_offset=0x48))

    # =========================================================================
    # SECTION 8: Full E4 block content comparison
    # =========================================================================
    print("=" * 80)
    print("SECTION 8: Full E4 block content (for reference)")
    print("=" * 80)
    for key in keys:
        ei = e4_info[key]
        e4_data = bodies[key][ei['start']:ei['end']]
        print(f"\n  --- {key} (body[{hex(ei['start'])}:{hex(ei['end'])}], {ei['size']}B) ---")
        print(hex_dump(e4_data, offset=ei['start']))
        print(f"  Records:")
        for idx, (type_id, size, rec) in enumerate(ei['recs']):
            sep_val = ei['seps'][idx] if idx < len(ei['seps']) else None
            type_str = f'type={type_id:#04x}' if type_id is not None else 'Pulse  '
            sep_str = f'sep={sep_val:#04x}' if sep_val is not None else ''
            print(f"    step{idx:2d}: {type_str} {size}B [{rec.hex(' ')}] {sep_str}")

    # =========================================================================
    # SECTION 9: Post-E4 body (full remainder) comparison
    # =========================================================================
    print()
    print("=" * 80)
    print("SECTION 9: Post-E4 remainder (everything after E4 block to end)")
    print("=" * 80)
    for key in keys:
        ei = e4_info[key]
        remainder = bodies[key][ei['end']:]
        print(f"\n  --- {key} (body[{hex(ei['end'])}:], {len(remainder)}B) ---")
        print(hex_dump(remainder, offset=ei['end']))

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == '__main__':
    main()
