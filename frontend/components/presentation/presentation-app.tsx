"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ACCESS } from "@/lib/presentation/config";
import { PassphraseGate } from "./passphrase-gate";
import { Deck } from "./deck";

/**
 * Client root of Presentation Mode. Handles the secret unlock (localStorage or
 * a `?key=` query param) and then renders the keynote deck. Renders nothing on
 * first paint to avoid a hydration mismatch, then reveals the correct view.
 */
export function PresentationApp() {
  const router = useRouter();
  const [unlocked, setUnlocked] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let ok = false;
    try {
      ok = localStorage.getItem(ACCESS.unlockStorageKey) === "1";
      const key = new URLSearchParams(window.location.search).get("key");
      if (!ok && key && key === ACCESS.passphrase) {
        ok = true;
        localStorage.setItem(ACCESS.unlockStorageKey, "1");
      }
    } catch {
      /* storage/URL access unavailable */
    }
    // SSR-safe, client-only read of the unlock state on mount. Kept in an
    // effect (not a lazy initializer) so server and client first paint match.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUnlocked(ok);
    setReady(true);
  }, []);

  if (!ready) return null;
  if (!unlocked) return <PassphraseGate onUnlock={() => setUnlocked(true)} />;
  return <Deck onExit={() => router.push("/dashboard")} />;
}
