"use client";
import { useEffect, useState } from "react";

/**
 * Returns `true` once the pointer/keyboard has been idle for `delay` ms while
 * `active`. Used to hide the cursor and auto-hide the control bar during a
 * running presentation. Any input resets the timer.
 */
export function useIdleCursor(active: boolean, delay = 2800): boolean {
  const [idle, setIdle] = useState(false);

  useEffect(() => {
    if (!active) return;
    let timer: number;
    const reset = () => {
      setIdle(false);
      window.clearTimeout(timer);
      timer = window.setTimeout(() => setIdle(true), delay);
    };
    const passive: AddEventListenerOptions = { passive: true };
    // Schedule the first idle transition without a synchronous state write.
    timer = window.setTimeout(() => setIdle(true), delay);
    window.addEventListener("mousemove", reset, passive);
    window.addEventListener("mousedown", reset, passive);
    window.addEventListener("wheel", reset, passive);
    window.addEventListener("keydown", reset);
    window.addEventListener("touchstart", reset, passive);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("mousemove", reset);
      window.removeEventListener("mousedown", reset);
      window.removeEventListener("wheel", reset);
      window.removeEventListener("keydown", reset);
      window.removeEventListener("touchstart", reset);
    };
  }, [active, delay]);

  // When inactive, always report "not idle" regardless of the last known value.
  return active ? idle : false;
}
