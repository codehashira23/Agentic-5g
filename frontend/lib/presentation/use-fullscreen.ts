"use client";
import { useCallback, useEffect, useState, type RefObject } from "react";

type FsDocument = Document & {
  webkitFullscreenElement?: Element | null;
  webkitExitFullscreen?: () => Promise<void> | void;
};
type FsElement = HTMLElement & {
  webkitRequestFullscreen?: () => Promise<void> | void;
};

/**
 * Cross-browser Fullscreen API wrapper. Requests fullscreen on the given
 * element (falling back to the document). If the browser blocks it, the deck
 * still fills the viewport via its fixed overlay, so this degrades gracefully.
 */
export function useFullscreen(ref: RefObject<HTMLElement | null>) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const onChange = () => {
      const d = document as FsDocument;
      setIsFullscreen(Boolean(document.fullscreenElement || d.webkitFullscreenElement));
    };
    document.addEventListener("fullscreenchange", onChange);
    document.addEventListener("webkitfullscreenchange", onChange as EventListener);
    onChange();
    return () => {
      document.removeEventListener("fullscreenchange", onChange);
      document.removeEventListener("webkitfullscreenchange", onChange as EventListener);
    };
  }, []);

  const enter = useCallback(async () => {
    const el = (ref.current ?? document.documentElement) as FsElement;
    try {
      if (el.requestFullscreen) await el.requestFullscreen();
      else if (el.webkitRequestFullscreen) await el.webkitRequestFullscreen();
    } catch {
      /* Fullscreen may be blocked (e.g. iframe/permissions) — overlay still covers the viewport. */
    }
  }, [ref]);

  const exit = useCallback(async () => {
    const d = document as FsDocument;
    try {
      if (document.fullscreenElement && document.exitFullscreen) await document.exitFullscreen();
      else if (d.webkitFullscreenElement && d.webkitExitFullscreen) await d.webkitExitFullscreen();
    } catch {
      /* no-op */
    }
  }, []);

  const toggle = useCallback(() => {
    if (isFullscreen) void exit();
    else void enter();
  }, [isFullscreen, enter, exit]);

  return { isFullscreen, enter, exit, toggle };
}
