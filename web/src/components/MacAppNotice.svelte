<aside
  class="mac-app-notice web-only"
  data-web-only="true"
  aria-label="XYBuddy for Mac"
>
  <div>
    <p class="notice-kicker">Mac companion</p>
    <p class="notice-copy">
      XYBuddy for Mac is coming soon for direct OP-XY USB transfer and project
      backup.
    </p>
  </div>
  <span title="Mac app download is not available yet">coming soon</span>
</aside>

<style>
  .mac-app-notice {
    display: flex;
    width: min(640px, 100%);
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

  .notice-kicker,
  .mac-app-notice span {
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

  .mac-app-notice span {
    border: 1px solid rgba(247, 247, 242, 0.16);
    padding: 6px 8px;
  }

  @media (max-width: 620px) {
    .mac-app-notice {
      align-items: flex-start;
      flex-direction: column;
      gap: 10px;
    }
  }
</style>
