<script lang="ts">
  export let processing = false;
</script>

<span class="popover-file-tags" class:processing aria-hidden="true">
  <span>.mid</span>
  <span>.xy</span>
</span>

<style>
  .popover-file-tags {
    position: absolute;
    top: -34px;
    left: 50%;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    opacity: 0;
    pointer-events: none;
    transform: translateX(-50%);
    animation: file-tags-pop 520ms cubic-bezier(0.22, 1, 0.36, 1) 720ms both;
  }

  .popover-file-tags.processing {
    opacity: 0;
  }

  .popover-file-tags span {
    min-width: 38px;
    padding: 5px 8px 6px;
    border: 1px solid rgba(247, 247, 242, 0.22);
    border-radius: 999px;
    background: rgba(5, 5, 5, 0.74);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.22);
    color: rgba(247, 247, 242, 0.7);
    font-size: 11px;
    font-weight: 460;
    line-height: 1;
    text-align: center;
    text-transform: lowercase;
    animation: file-tag-float 5.8s ease-in-out 1.34s infinite;
  }

  .popover-file-tags span:nth-child(2) {
    animation-delay: 1.72s;
  }

  @keyframes file-tags-pop {
    0% {
      opacity: 0;
      transform: translateX(-50%) translateY(8px) scale(0.82);
    }

    64% {
      opacity: 1;
      transform: translateX(-50%) translateY(-3px) scale(1.06);
    }

    100% {
      opacity: 1;
      transform: translateX(-50%) translateY(0) scale(1);
    }
  }

  @keyframes file-tag-float {
    0%,
    100% {
      opacity: 0.5;
      transform: translateY(0) rotate(-1deg);
    }

    45% {
      opacity: 0.78;
      transform: translateY(-4px) rotate(1.5deg);
    }
  }

  @media (max-width: 620px) {
    .popover-file-tags {
      top: -29px;
      gap: 6px;
    }

    .popover-file-tags span {
      min-width: 33px;
      padding: 4px 7px 5px;
      font-size: 10px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .popover-file-tags {
      opacity: 1;
      transform: translateX(-50%);
      animation: none;
    }

    .popover-file-tags span {
      opacity: 0.68;
      transform: none;
      animation: none;
    }
  }
</style>
