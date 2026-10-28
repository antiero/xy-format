# Guide screenshots

Captured on 25 October 2026 from the XYBuddy Xcode project in the sibling
TEBuddy checkout. All images are real native app or Xcode Simulator captures;
no generated or composited interfaces are used.

## Mac — connected OP–XY

Captured on 28 October 2026 by `script/capture-mac-screenshots.sh` in the
TEBuddy checkout, which drives a Debug build of the app through each view
and captures its window without the shadow. Rerun it after UI changes; see
the script's `--help`. The window is 1440 × 900 points, captured at 2× as
2880 × 1800, which is also a Mac App Store screenshot size. The OP–XY was
connected over USB on firmware 1.2.1.

- `mac-song.png`: the import workspace, before a project is opened.
- `mac-files.png`, `mac-templates.png`, `mac-presets.png`, `mac-samples.png`:
  real MTP directory listings in all four Files areas.
- `mac-backup.png`: MTP-connected device details, backup options and existing
  snapshot history. No backup or restore was started.
- `mac-arrange.png`, `mac-pattern.png`, `mac-song-mode.png`: `7nderground.xy`
  opened read-only from the connected device into Song. No edits were sent
  back to the instrument.
- `mac-live-remote.png`: Live Remote with OP–XY over USB MIDI, after leaving
  MTP mode. No transport or scene commands were sent.
- `mac-edit.png`: that arrangement opened in the native piano roll.
- `mac-capture.png`: OP–XY USB audio selected, eight inputs and live meters.
  No recording was started.

The script switches OP–XY into MTP mode for Files and Backup and ejects it
back to USB MIDI/audio mode afterwards. No files were uploaded, deleted or
renamed.

## iPhone and iPad — simulator

Images were captured with `simctl io screenshot`. Status time is 09:41.
The OP–XY was connected to the Mac, not the simulated mobile devices.
Captions explicitly distinguish simulator state from connected hardware.

- `iphone-song.png`, `iphone-capture.png`, `iphone-files.png`,
  `iphone-backup.png`: all four tabs on iPhone 18 Pro, iOS 27.0.
- `ipad-song.png`, `ipad-edit.png`, `ipad-capture.png`, `ipad-files.png`,
  `ipad-backup.png`: all five tabs on iPad Pro 11-inch (M5), iOS 27.0,
  landscape. The Edit example contains four notes entered through the app's
  drawing tool, in simulator memory only.
- Existing local backup history is shown as found; it was not generated for
  these screenshots. Mobile Files shows the real disconnected state and
  Capture shows the simulator's input state, not USB hardware acceptance.

## Presentation

`screenshots.js` lists every view and its source caption. Each chapter has a
labelled native select for switching views and a link to the full-resolution
original. Only the selected image loads. The import screenshot remains in
the introduction so the page also has a screenshot without JavaScript.

The static guide is copied to `dist/docs` by the existing Vite build. No new
dependencies are required. Preview `/docs/` from the built static directory,
or `/docs/index.html` with the Vite development server.
