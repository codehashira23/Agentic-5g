"use client";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ACCESS } from "@/lib/presentation/config";

/**
 * Global secret key combos. Typed anywhere in the app (outside a text field)
 * within a short window, they navigate to a hidden route. Renders nothing.
 *
 *   g → p   Presentation deck  (/__present)
 *   g → d   Internal docs      (/internal)
 *
 * Routes/sequences are kept inline (not imported from the docs/deck bundles) so
 * this always-mounted listener stays tiny.
 */
const HOTKEYS: { sequence: readonly string[]; route: string }[] = [
  { sequence: ACCESS.hotkeySequence, route: ACCESS.route }, // g p → presentation deck
  { sequence: ["g", "d"], route: "/internal" }, // g d → internal docs walkthrough
];

export function SecretHotkey() {
  const router = useRouter();
  const buffer = useRef<{ keys: string[]; time: number }>({ keys: [], time: 0 });

  useEffect(() => {
    const hotkeys = HOTKEYS.map((h) => ({
      route: h.route,
      seq: h.sequence.map((k) => k.toLowerCase()),
    }));
    const maxLen = Math.max(...hotkeys.map((h) => h.seq.length));

    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (
        el &&
        (el.tagName === "INPUT" ||
          el.tagName === "TEXTAREA" ||
          el.tagName === "SELECT" ||
          el.isContentEditable)
      ) {
        return;
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const now = Date.now();
      const buf = buffer.current;
      if (now - buf.time > ACCESS.hotkeyWindowMs) buf.keys = [];
      buf.time = now;
      buf.keys.push(e.key.toLowerCase());
      if (buf.keys.length > maxLen) buf.keys = buf.keys.slice(-maxLen);

      for (const hk of hotkeys) {
        const tail = buf.keys.slice(-hk.seq.length);
        if (tail.length === hk.seq.length && hk.seq.every((k, i) => tail[i] === k)) {
          buf.keys = [];
          router.push(hk.route);
          break;
        }
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  return null;
}
