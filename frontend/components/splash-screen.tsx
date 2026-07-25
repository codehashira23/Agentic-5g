"use client";
import { useEffect, useState } from "react";

/**
 * Cinematic first-load splash — expanding 5G signal rings, glowing core node,
 * animated Agent5G wordmark, tagline, and a loading bar. Shows once per tab
 * session, then fades out and unmounts.
 */
export function SplashScreen() {
  const [phase, setPhase] = useState<"loading" | "out" | "hidden">("loading");

  useEffect(() => {
    if (typeof window === "undefined") return;
    // Only show once per browser tab session
    if (sessionStorage.getItem("a5g_splash_shown")) {
      setPhase("hidden");
      return;
    }
    const startFade = setTimeout(() => setPhase("out"), 2600);
    const remove = setTimeout(() => {
      setPhase("hidden");
      sessionStorage.setItem("a5g_splash_shown", "1");
    }, 3300);
    return () => {
      clearTimeout(startFade);
      clearTimeout(remove);
    };
  }, []);

  if (phase === "hidden") return null;

  return (
    <div className={`splash-root ${phase === "out" ? "splash-out" : ""}`} aria-hidden>
      {/* Signal rings + core */}
      <div className="splash-rings">
        <span className="splash-ring" />
        <span className="splash-ring" />
        <span className="splash-ring" />
        <span className="splash-ring" />
        <div className="splash-core">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"
               strokeLinecap="round" strokeLinejoin="round">
            <path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9" />
            <path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5" />
            <circle cx="12" cy="12" r="2" fill="white" stroke="none" />
            <path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5" />
            <path d="M19.1 4.9C23 8.8 23 15.2 19.1 19.1" />
          </svg>
        </div>
      </div>

      {/* Wordmark */}
      <div className="flex flex-col items-center gap-2">
        <h1 className="splash-wordmark brand-gradient">AGENT5G</h1>
        <p className="splash-tagline">Agentic AI · 5G Advanced Release 20</p>
      </div>

      {/* Loading bar */}
      <div className="splash-bar">
        <div className="splash-bar-fill" />
      </div>
    </div>
  );
}
