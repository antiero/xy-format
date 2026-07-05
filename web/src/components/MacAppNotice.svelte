<aside
  class="mac-app-notice web-only"
  data-web-only="true"
  aria-label="XYBuddy for Mac"
>
  <div class="notice-content">
    <img class="notice-icon" src="/favicon.svg" alt="" aria-hidden="true" />
    <div>
      <p class="notice-kicker">xybuddy app</p>
      <p class="notice-copy">Coming soon to macOS</p>
    </div>
  </div>
  <a
    href="https://testflight.apple.com/join/Hg8CwZNE"
    target="_blank"
    rel="noreferrer"
    aria-label="Join the XYBuddy for Mac TestFlight"
    title="Join the XYBuddy for Mac TestFlight"
  >
    <img src="/testflight.svg" alt="" aria-hidden="true" />
    <span>try now</span>
  </a>
</aside>

<style>
  .mac-app-notice {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 11px 13px;
    border: 1px solid rgba(247, 247, 242, 0.12);
    background: rgba(247, 247, 242, 0.026);
    color: var(--xy-text-muted);
  }

  .notice-kicker,
  .notice-copy {
    margin: 0;
  }

  .notice-content {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 10px;
  }

  .notice-icon {
    width: 28px;
    height: 28px;
    flex: 0 0 auto;
    opacity: 0.9;
  }

  .notice-kicker,
  .mac-app-notice a {
    color: var(--xy-text-dim);
    font-size: 10px;
    line-height: 1;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .notice-copy {
    margin-top: 5px;
    color: var(--xy-text-muted);
    font-size: 12px;
    line-height: 1.45;
  }

  .mac-app-notice a {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    border: 1px solid rgba(247, 247, 242, 0.16);
    padding: 6px 8px;
    text-decoration: none;
  }

  .mac-app-notice a img {
    width: 14px;
    height: 14px;
    opacity: 0.76;
  }

  .mac-app-notice a:hover,
  .mac-app-notice a:focus-visible {
    border-color: rgba(247, 247, 242, 0.42);
    color: var(--xy-text);
  }

  @media (max-width: 620px) {
    .mac-app-notice {
      align-items: center;
      flex-direction: column;
      gap: 10px;
    }

    .notice-content {
      align-items: flex-start;
    }
  }
</style>
