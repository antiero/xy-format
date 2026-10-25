# Guide screenshots

Captured on 25 October 2026 from the XYBuddy Xcode project in the sibling
TEBuddy checkout. All images are real native app or Xcode Simulator captures;
no generated or composited interfaces are used.

## Mac — connected OP–XY

The native Debug app built earlier in this session was run with the user's
USB-connected OP–XY, reporting firmware 1.2.0. Captures were cropped to the
1352 × 849-point app window at 2× resolution.

- `mac-song.png`: original import workspace, captured before connection.
- `mac-arrange.png`, `mac-pattern.png`, `mac-song-mode.png`: the existing
  `7nderground.xy` project opened read-only from the connected device into
  Song. No edits were sent back to the instrument.
- `mac-edit.png`: that arrangement opened in the native piano roll.
- `mac-files.png`, `mac-templates.png`, `mac-presets.png`, `mac-samples.png`:
  real MTP directory listings in all four Files areas.
- `mac-backup.png`: MTP-connected device details, backup options and existing
  snapshot history. No backup or restore was started for this capture.
- `mac-sample-browser.png`: the Song sample drawer listing device samples.
- `mac-live-remote.png`: OP–XY detected over USB MIDI after leaving MTP mode.
  No transport or scene commands were triggered for the screenshot.
- `mac-capture.png`: OP–XY USB audio selected, eight inputs and live meter
  activity. No recording was started; this is input-meter evidence only.

The file connection was ejected after capturing MTP views. The instrument
was left in USB MIDI/audio mode. No files were uploaded, deleted or renamed.

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
