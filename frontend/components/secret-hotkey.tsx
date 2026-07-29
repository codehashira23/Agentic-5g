"use client";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ACCESS } from "@/lib/presentation/config";

/**
 * Global secret key combo. Pressing the configured sequence (default: "g" then
 * "p") anywhere in the app — outside a text field — navigates to the hidden
 * Presentation Mode route. Renders nothing; just a listener.
 */
export function SecretHotkey() {
  const router = useRouter();
  const buffer = useRef<{ keys: string[]; time: number }>({ keys: [], time: 0 });

  useEffect(() => {
    const seq = ACCESS.hotkeySequence.map((k) => k.toLowerCase());

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
      if (buf.keys.length > seq.length) buf.keys = buf.keys.slice(-seq.length);

      if (buf.keys.length === seq.length && seq.every((k, i) => buf.keys[i] === k)) {
        buf.keys = [];
        router.push(ACCESS.route);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  return null;
}
