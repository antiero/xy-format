"""Populate `.preset` folders with sample files referenced by patch.json.

Probe fixtures keep audio assets deduplicated in a shared asset directory.
Before copying a preset experiment to the OP-XY, run this script to materialize
the WAV files each `.preset` folder needs.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESETS = ROOT / "src" / "preset-load-experiments" / "2026-06-patch-json-fields" / "presets"
DEFAULT_ASSETS = ROOT / "src" / "preset-load-experiments" / "assets"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "presets",
        nargs="?",
        type=Path,
        default=DEFAULT_PRESETS,
        help="directory containing .preset folders",
    )
    parser.add_argument(
        "--assets",
        action="append",
        type=Path,
        default=[],
        help="directory or file to search for sample assets; may be repeated",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned copies without writing files",
    )
    args = parser.parse_args()

    presets_dir = _resolve(args.presets)
    asset_roots = [_resolve(path) for path in args.assets] or [DEFAULT_ASSETS]
    assets = _index_assets(asset_roots)
    copied = 0
    missing: list[str] = []

    for preset_dir in sorted(presets_dir.glob("*.preset")):
        patch_path = preset_dir / "patch.json"
        if not patch_path.exists():
            continue
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
        for sample in sorted(_sample_refs(patch)):
            source = _find_asset(sample, assets)
            target = preset_dir / Path(sample).name
            if source is None:
                missing.append(f"{preset_dir.name}: {sample}")
                continue
            if target.exists() and target.read_bytes() == source.read_bytes():
                continue
            print(f"{source} -> {target}")
            if not args.dry_run:
                shutil.copy2(source, target)
            copied += 1

    if missing:
        detail = "\n".join(f"  - {item}" for item in missing)
        raise SystemExit(f"missing sample assets:\n{detail}")
    print(f"populated {copied} sample file(s)")


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else (ROOT / path)


def _index_assets(paths: list[Path]) -> dict[str, Path]:
    assets: dict[str, Path] = {}
    for root in paths:
        if root.is_file():
            assets[root.name] = root
            continue
        for path in root.rglob("*"):
            if path.is_file():
                assets.setdefault(path.name, path)
    return assets


def _find_asset(sample: str, assets: dict[str, Path]) -> Path | None:
    return assets.get(Path(sample).name)


def _sample_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        sample = value.get("sample")
        if isinstance(sample, str) and sample:
            refs.add(sample)
        for child in value.values():
            refs.update(_sample_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_sample_refs(child))
    return refs


if __name__ == "__main__":
    main()
