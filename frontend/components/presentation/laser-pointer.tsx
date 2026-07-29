"use client";
import { useEffect, useRef } from "react";

/**
 * Glowing red laser dot that tracks the cursor when active. Position is set
 * imperatively (no React state) so it stays at 60fps.
 */
export function LaserPointer({ active }: { active: boolean }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active) return;
    const move = (e: MouseEvent) => {
      const el = ref.current;
      if (el) el.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0)`;
    };
    window.addEventListener("mousemove", move, { passive: true });
    return () => window.removeEventListener("mousemove", move);
  }, [active]);

  if (!active) return null;
  return <div ref={ref} className="pv-laser" aria-hidden />;
}
