"use client";
import { useEffect, useRef, type RefObject, type TouchEvent as ReactTouchEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { PROJECT } from "@/lib/presentation/config";
import { useDeck } from "@/lib/presentation/deck-context";
import { slideVariants } from "@/lib/presentation/motion";
import { useIdleCursor } from "@/lib/presentation/use-idle-cursor";
import { SLIDE_ORDER } from "@/lib/presentation/config";
import { SLIDES } from "./slide-registry";
import { Backgrounds } from "./backgrounds";
import { Controls } from "./controls";
import { Overview } from "./overview";
import { ShortcutsHelp } from "./shortcuts-help";
import { PresenterNotes } from "./presenter-notes";
import { LaserPointer } from "./laser-pointer";
import { LaunchScreen } from "./launch-screen";

const NAV_LOCK_MS = 620;

export function DeckStage({ rootRef }: { rootRef: RefObject<HTMLElement | null> }) {
  const d = useDeck();
  const idle = useIdleCursor(d.started && !d.overview && !d.help);
  const audioRef = useRef<HTMLAudioElement>(null);
  const navLock = useRef(0);
  const touch = useRef<{ x: number; y: number } | null>(null);

  const meta = SLIDES[d.slideId];
  const Slide = meta.Component;

  /* Lock document scroll while the deck is mounted. */
  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const prev = { htmlO: html.style.overflow, bodyO: body.style.overflow, over: body.style.overscrollBehavior };
    html.style.overflow = "hidden";
    body.style.overflow = "hidden";
    body.style.overscrollBehavior = "none";
    return () => {
      html.style.overflow = prev.htmlO;
      body.style.overflow = prev.bodyO;
      body.style.overscrollBehavior = prev.over;
    };
  }, []);

  /* Preload the neighbouring slides so transitions never flash. */
  useEffect(() => {
    const nextId = SLIDE_ORDER[Math.min(SLIDE_ORDER.length - 1, d.index + 1)];
    const prevId = SLIDE_ORDER[Math.max(0, d.index - 1)];
    void SLIDES[nextId].preload();
    void SLIDES[prevId].preload();
  }, [d.index]);

  /* Background music toggle. */
  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    if (d.music) el.play().catch(() => void d.toggleMusic());
    else el.pause();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [d.music]);

  /* Keyboard navigation + shortcuts. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const k = e.key;
      const target = e.target as HTMLElement | null;
      const interactive =
        !!target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if (interactive) return;

      if (k === "Escape") {
        e.preventDefault();
        if (d.help) return d.setHelp(false);
        if (d.overview) return d.setOverview(false);
        if (d.isFullscreen) return d.exitFullscreen();
        return d.exitPresentation();
      }
      if (k === "h" || k === "H" || k === "?") {
        e.preventDefault();
        return d.toggleHelp();
      }

      switch (k) {
        case "ArrowRight":
        case "PageDown":
          e.preventDefault();
          return d.next();
        case " ":
          // let a focused button handle its own Space
          if (target?.tagName === "BUTTON" || target?.tagName === "A") return;
          e.preventDefault();
          return d.next();
        case "ArrowLeft":
        case "PageUp":
          e.preventDefault();
          return d.prev();
        case "ArrowDown":
          e.preventDefault();
          return d.next();
        case "ArrowUp":
          e.preventDefault();
          return d.prev();
        case "Home":
          e.preventDefault();
          return d.goTo(0);
        case "End":
          e.preventDefault();
          return d.goTo(d.total - 1);
        case "f":
        case "F":
          return d.toggleFullscreen();
        case "o":
        case "O":
          return d.toggleOverview();
        case "a":
        case "A":
          return d.toggleAutoplay();
        case "n":
        case "N":
          return d.toggleNotes();
        case "l":
        case "L":
          return d.toggleLaser();
        case "m":
        case "M":
          return d.toggleMusic();
        case "t":
        case "T":
          return d.toggleTheme();
        default:
          if (/^[1-9]$/.test(k)) {
            e.preventDefault();
            d.goTo(Number(k) - 1);
          }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [d]);

  /* Mouse-wheel navigation (debounced so one gesture = one slide). */
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (d.overview) return;
      if (Math.abs(e.deltaY) < 18) return;
      e.preventDefault();
      const now = Date.now();
      if (now - navLock.current < NAV_LOCK_MS) return;
      navLock.current = now;
      if (e.deltaY > 0) d.next();
      else d.prev();
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [d, rootRef]);

  /* Touch swipe navigation. */
  const onTouchStart = (e: ReactTouchEvent) => {
    const t = e.touches[0];
    touch.current = { x: t.clientX, y: t.clientY };
  };
  const onTouchEnd = (e: ReactTouchEvent) => {
    if (!touch.current) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - touch.current.x;
    const dy = t.clientY - touch.current.y;
    touch.current = null;
    if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy)) return;
    if (dx < 0) d.next();
    else d.prev();
  };

  const hideCursor = d.laser || (idle && d.started);

  return (
    <div
      ref={rootRef as RefObject<HTMLDivElement>}
      className={`pv-root ${d.theme === "light" ? "light" : ""} ${hideCursor ? "pv-hide-cursor" : ""} bg-base text-primary`}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      <Backgrounds parallax={d.index} />

      {/* Slide host */}
      <div className="absolute inset-0">
        <AnimatePresence custom={d.direction} initial={false}>
          <motion.div
            key={d.slideId}
            custom={d.direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            className="absolute inset-0"
          >
            <Slide />
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Overlays */}
      <PresenterNotes />
      <Overview />
      <ShortcutsHelp />
      <Controls visible={!idle || !d.started} />
      <LaserPointer active={d.laser} />
      <LaunchScreen />

      {/* Background music (only if an asset is present at PROJECT.musicUrl) */}
      <audio ref={audioRef} src={PROJECT.musicUrl} loop preload="none" />
    </div>
  );
}
