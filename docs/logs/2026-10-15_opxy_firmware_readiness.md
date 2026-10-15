# OP-XY OS 1.2.0 readiness

Date: 2026-10-15

## Confirmed release surface

Teenage Engineering's OP-XY download page lists OS 1.2.0 with multi-channel USB audio, Drumline, the dynamic track filter with drive, the detune preset setting, and improved bootloader security.

Device screenshots supplied for this work show the USB audio choices `2 ch`, `2 ch (custom)`, and `8 ch`. In `8 ch`, tracks 1-8 are routed diagonally to USB channels 1-8. The device warns that this mode uses more CPU and may reduce voice count.

## Readiness boundary

- Existing corpus-proven container headers `09130386` and `09130686` remain editable.
- A structurally valid but unknown header opens read-only, retains the original bytes, and cannot enter an edit or device-transfer path.
- RLE decoding stops at 2 MiB of decoded project data.
- General OP-XY OS 1.2.0 project editing and device writes remain disabled while the new container header and unmapped 1.2.0 fields are under review.
- Drumline, filter drive, and detune are not mapped from release notes alone. They require controlled device-authored fixture diffs.
- The two device-authored Drumline captures use header `ddccbbaa09140786` and the established 289,521-byte decoded layout. All assigned tracks passed preset-identity, one-pattern, and zero-note validation. The nine unique Drumline donors are now available in the web preset chooser; this bounded opaque-track reuse does not enable general 1.2.0 project editing.

## Native discovery

The macOS app exposes a feature-flagged Diagnostics command that saves a schema-v1 JSON inventory of CoreAudio devices and CoreMIDI endpoints. It records channel counts, sample-rate capabilities, transport, and buffer size without opening an audio stream or requesting microphone access.

## Physical acceptance still required

Initial checks did not enumerate the OP-XY. After reconnecting with a stable data-capable cable, macOS identified:

- CoreAudio `OP-XY`, manufactured by teenage engineering, over USB;
- 2 input channels and 2 output channels at 44.1 kHz;
- one CoreMIDI source and one CoreMIDI destination, both named `OP-XY`;
- the expected teenage engineering USB device in MIDI/USB-audio mode, with MTP unavailable while `MIDIServer` owns it.

This confirms a stable data connection. After re-selecting `8 ch` on the device, CoreAudio re-enumerated the OP-XY as **8 input channels and 2 output channels at 44.1 kHz** while the CoreMIDI endpoints remained available. This is host-side discovery proof for the new multi-channel USB mode; it is not yet a recorded-audio or per-track signal-routing test.

The two Drumline projects were retrieved and accepted. `drumline01.xy` supplies `atom` through `tyche` on Tracks 1–8; `drumline02.xy` contains `we will c` on Tracks 1–8, with Track 1 used as the canonical donor.
