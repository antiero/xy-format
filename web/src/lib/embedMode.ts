type EmbedModeContext = {
  search: string;
  userAgent: string;
  platform?: string;
  maxTouchPoints?: number;
  nativeAppGlobal?: unknown;
  nativeBridge?: unknown;
};

declare global {
  interface Window {
    XYBUDDY_NATIVE_APP?: boolean;
  }
}

function isNativeEmbedContext(context: EmbedModeContext): boolean {
  const params = new URLSearchParams(context.search);

  return (
    params.get("embed") === "macos" ||
    params.get("xybuddyApp") === "1" ||
    Boolean(context.nativeAppGlobal) ||
    Boolean(context.nativeBridge) ||
    context.userAgent.includes("XYBuddyMac")
  );
}

export function isXYBuddyNativeEmbed(
  context?: Partial<EmbedModeContext>,
): boolean {
  if (context) {
    return isNativeEmbedContext({
      search: context.search ?? "",
      userAgent: context.userAgent ?? "",
      nativeAppGlobal: context.nativeAppGlobal,
      nativeBridge: context.nativeBridge,
    });
  }

  if (typeof window === "undefined") return false;

  return isNativeEmbedContext({
    search: window.location.search,
    userAgent: window.navigator.userAgent,
    nativeAppGlobal: window.XYBUDDY_NATIVE_APP,
    nativeBridge: (window as { __xyBuddyNativeBridge?: unknown })
      .__xyBuddyNativeBridge,
  });
}

export function isAppleClient(context?: Partial<EmbedModeContext>): boolean {
  const userAgent =
    context?.userAgent ??
    (typeof navigator === "undefined" ? "" : navigator.userAgent);
  const platform =
    context?.platform ??
    (typeof navigator === "undefined" ? "" : navigator.platform);
  const maxTouchPoints =
    context?.maxTouchPoints ??
    (typeof navigator === "undefined" ? 0 : navigator.maxTouchPoints);

  if (/\b(iPhone|iPad|iPod)\b/i.test(userAgent)) return true;
  if (/\b(visionOS|Vision|Apple Vision)\b/i.test(userAgent)) return true;
  if (/\b(Macintosh|Mac OS X)\b/i.test(userAgent)) return true;
  if (/\b(iPhone|iPad|iPod|Mac)\b/i.test(platform)) return true;

  return platform === "MacIntel" && maxTouchPoints > 1;
}

export function applyNativeEmbedClass(): boolean {
  if (typeof document === "undefined") return false;

  const isNativeEmbed = isXYBuddyNativeEmbed();
  document.documentElement.classList.toggle(
    "xybuddy-native-embed",
    isNativeEmbed,
  );
  return isNativeEmbed;
}
