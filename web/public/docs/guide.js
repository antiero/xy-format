const links = [...document.querySelectorAll('nav a[href^="#"]')];
const observer = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      for (const link of links) {
        if (link.hash === `#${entry.target.id}`)
          link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      }
    }
  },
  { rootMargin: "-15% 0px -60% 0px" },
);
document
  .querySelectorAll("main section[id]")
  .forEach((section) => observer.observe(section));

const toggle = document.querySelector("#contents-toggle");
const contents = document.querySelector("#guide-contents");
const narrow = window.matchMedia("(max-width: 850px)");
function setContents(open) {
  document.body.classList.toggle("contents-hidden", !open);
  toggle.setAttribute("aria-expanded", String(open));
  toggle.setAttribute("aria-label", open ? "Hide contents" : "Show contents");
  toggle.title = open ? "Hide contents" : "Show contents";
  contents.inert = !open;
}
setContents(!narrow.matches);
toggle.addEventListener("click", () =>
  setContents(toggle.getAttribute("aria-expanded") !== "true"),
);
narrow.addEventListener("change", () => setContents(!narrow.matches));
contents.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    setContents(false);
    toggle.focus();
  }
});
contents.addEventListener("click", (event) => {
  if (narrow.matches && event.target.closest('a[href^="#"]')) {
    setContents(false);
    toggle.focus({ preventScroll: true });
  }
});
