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
