// Original native captures only. See SCREENSHOTS.md for capture provenance.
const desktop = "macOS app";
const simulator = "Xcode Simulator · no USB instrument connected";
const galleries = {
  song: [
    [
      "Mac · Arrange",
      "mac-arrange",
      "A project opened from OP–XY over MTP, showing its track patterns and scenes.",
      desktop,
    ],
    [
      "Mac · Pattern",
      "mac-pattern",
      "Pattern editing with step buttons, note lanes, sound selection and timing controls.",
      desktop,
    ],
    [
      "Mac · Song",
      "mac-song-mode",
      "The song’s sequence of six scenes, with tempo and transport controls.",
      desktop,
    ],
    [
      "Mac · Live Remote",
      "mac-live-remote",
      "Live Remote with OP–XY connected over MIDI, alongside the Song workspace.",
      "macOS · USB MIDI connected",
    ],
    [
      "Mac · Sample browser",
      "mac-sample-browser",
      "The sample drawer showing user samples from the connected OP–XY.",
      "macOS · MTP connected",
    ],
    [
      "Mac · Import",
      "mac-song",
      "The Song import workspace and native room toolbar.",
      desktop,
    ],
    [
      "iPhone · Song",
      "iphone-song",
      "The Song import workspace with the four native iPhone tabs.",
      simulator,
    ],
    [
      "iPad · Song",
      "ipad-song",
      "The Song import workspace with the additional iPad Edit tab.",
      simulator,
    ],
  ],
  edit: [
    [
      "Mac · Edit",
      "mac-edit",
      "Native piano roll with notes and velocities loaded from the Song arrangement.",
      desktop,
    ],
    [
      "iPad · Edit",
      "ipad-edit",
      "Native touch piano roll with a short example entered using the drawing tool.",
      simulator,
    ],
  ],
  files: [
    [
      "Mac · Projects",
      "mac-files",
      "Projects listed directly from OP–XY, with names, types and file sizes.",
      "macOS · MTP connected",
    ],
    [
      "Mac · Templates",
      "mac-templates",
      "The Templates area on the connected OP–XY.",
      "macOS · MTP connected",
    ],
    [
      "Mac · Presets",
      "mac-presets",
      "The Presets area showing a snapshot folder on OP–XY.",
      "macOS · MTP connected",
    ],
    [
      "Mac · Samples",
      "mac-samples",
      "User audio samples listed directly from OP–XY.",
      "macOS · MTP connected",
    ],
    [
      "iPhone · Files",
      "iphone-files",
      "The connection screen before an OP–XY is connected to iPhone.",
      simulator,
    ],
    [
      "iPad · Files",
      "ipad-files",
      "The connection screen before an OP–XY is connected to iPad.",
      simulator,
    ],
  ],
  backup: [
    [
      "Mac · Backup",
      "mac-backup",
      "Connected OP–XY firmware and storage information, backup categories and snapshot history.",
      "macOS · MTP connected · OS 1.2.0",
    ],
    [
      "iPhone · Backup",
      "iphone-backup",
      "Backup controls and existing local snapshot history on iPhone.",
      simulator,
    ],
    [
      "iPad · Backup",
      "ipad-backup",
      "Backup controls and existing local snapshot history on iPad.",
      simulator,
    ],
  ],
  capture: [
    [
      "Mac · Capture",
      "mac-capture",
      "Eight live OP–XY USB audio inputs with meter activity, recording controls and track labels.",
      "macOS · USB audio connected · live meters",
    ],
    [
      "iPhone · Capture",
      "iphone-capture",
      "Capture controls before a USB instrument is connected to iPhone.",
      simulator,
    ],
    [
      "iPad · Capture",
      "ipad-capture",
      "Capture controls before a USB instrument is connected to iPad.",
      simulator,
    ],
  ],
};

for (const gallery of document.querySelectorAll("[data-screenshots]")) {
  const key = gallery.dataset.screenshots;
  const shots = galleries[key];
  const toolbar = document.createElement("div");
  toolbar.className = "screenshot-toolbar";
  const label = document.createElement("label");
  label.htmlFor = `screenshot-${key}`;
  label.textContent = "App views";
  const select = document.createElement("select");
  select.id = label.htmlFor;
  select.setAttribute(
    "aria-label",
    `${key.charAt(0).toUpperCase() + key.slice(1)} screenshots`,
  );
  shots.forEach(([title], index) =>
    select.add(new Option(title, String(index))),
  );
  toolbar.append(label, select);
  const figure = document.createElement("figure");
  const link = document.createElement("a");
  const picture = document.createElement("img");
  picture.loading = "lazy";
  picture.decoding = "async";
  const caption = document.createElement("figcaption");
  caption.setAttribute("aria-live", "polite");
  link.append(picture);
  figure.append(link, caption);
  gallery.append(toolbar, figure);
  function showShot() {
    const [title, file, description, source] = shots[Number(select.value)];
    link.href = `/docs/images/${file}.png`;
    link.setAttribute("aria-label", `View full-size ${title} screenshot`);
    picture.alt = description;
    const phone = file.startsWith("iphone-");
    const tablet = file.startsWith("ipad-");
    picture.width = phone ? 1206 : tablet ? 2420 : 2704;
    picture.height = phone ? 2622 : tablet ? 1668 : 1698;
    gallery.dataset.platform = phone ? "iphone" : tablet ? "ipad" : "mac";
    picture.src = link.href;
    caption.textContent = `${title} · ${source}`;
  }
  select.addEventListener("change", showShot);
  showShot();
}

// Restore a deep link after the browser finishes its initial scroll restoration.
window.addEventListener("pageshow", () => {
  if (!window.location.hash) return;
  requestAnimationFrame(() => {
    document
      .getElementById(window.location.hash.slice(1))
      ?.scrollIntoView({ behavior: "instant" });
  });
});
