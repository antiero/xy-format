# Guide screenshots

Captured on 25 October 2026 from the XYBuddy Xcode project in the sibling
TEBuddy checkout. No composited or generated app interfaces are used.

- `images/mac-song.png`: native macOS app, built with the shared XYBuddy
  scheme, Debug configuration. Screen capture cropped to the app window.
- `images/iphone-song.png`: iPhone 18 Pro, iOS 27.0 Xcode Simulator,
  `simctl io screenshot`. Status bar time set to 09:41.
- `images/ipad-song.png`: iPad Pro 11-inch (M5), iOS 27.0 Xcode Simulator,
  landscape, `simctl io screenshot`.

Both native builds succeeded. These screenshots show the initial Song
workspace without an OP-XY connected; they do not demonstrate a physical
USB transfer or audio capture. Workflow copy was checked against
`Docs/XYBuddyArchitecture.md` and the current native view and model sources.

The guide is a standalone static page in `web/public/docs`, copied to
`dist/docs` by the existing Vite build. No new dependencies are required.
The deployed directory URL is `/docs/`. To preview locally, build the web
app and serve `dist` with a static server, or use `/docs/index.html` with
the Vite development server (whose `/docs/` route falls back to the SPA).
