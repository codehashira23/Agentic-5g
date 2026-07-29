/**
 * Gold-themed confetti celebration for the final slide.
 * canvas-confetti is imported dynamically so it never runs during SSR and
 * stays out of the initial bundle.
 */
const GOLD = ["#fca311", "#ffd166", "#ffe0a3", "#ffb733", "#ffffff"];

export async function fireConfetti(): Promise<void> {
  if (typeof window === "undefined") return;
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

  const confetti = (await import("canvas-confetti")).default;
  const end = Date.now() + 1100;

  // Two side cannons firing inward.
  (function frame() {
    confetti({
      particleCount: 5,
      angle: 60,
      spread: 62,
      origin: { x: 0, y: 0.65 },
      colors: GOLD,
      scalar: 1.05,
      zIndex: 10060,
    });
    confetti({
      particleCount: 5,
      angle: 120,
      spread: 62,
      origin: { x: 1, y: 0.65 },
      colors: GOLD,
      scalar: 1.05,
      zIndex: 10060,
    });
    if (Date.now() < end) requestAnimationFrame(frame);
  })();

  // One celebratory center burst.
  window.setTimeout(() => {
    confetti({
      particleCount: 140,
      spread: 100,
      startVelocity: 42,
      origin: { x: 0.5, y: 0.6 },
      colors: GOLD,
      zIndex: 10060,
    });
  }, 180);
}
