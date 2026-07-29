"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { SLIDE_ORDER, type SlideId } from "./config";
import { useFullscreen } from "./use-fullscreen";

export const AUTOPLAY_INTERVAL_MS = 7000;

export interface DeckContextValue {
  // navigation
  index: number;
  direction: number;
  total: number;
  slideId: SlideId;
  progress: number; // 0..1
  atStart: boolean;
  atEnd: boolean;
  goTo: (i: number) => void;
  next: () => void;
  prev: () => void;

  // ui panels / modes
  overview: boolean;
  toggleOverview: () => void;
  setOverview: (v: boolean) => void;
  help: boolean;
  toggleHelp: () => void;
  setHelp: (v: boolean) => void;
  notes: boolean;
  toggleNotes: () => void;

  // extras
  autoplay: boolean;
  toggleAutoplay: () => void;
  laser: boolean;
  toggleLaser: () => void;
  music: boolean;
  toggleMusic: () => void;
  theme: "dark" | "light";
  toggleTheme: () => void;

  // timer
  elapsedMs: number;
  resetTimer: () => void;

  // fullscreen
  isFullscreen: boolean;
  enterFullscreen: () => void;
  exitFullscreen: () => void;
  toggleFullscreen: () => void;

  // launch (Start Presentation gate)
  started: boolean;
  start: () => void;

  // leave the whole presentation (navigate back to the app)
  exitPresentation: () => void;
}

const DeckContext = createContext<DeckContextValue | null>(null);

export function useDeck(): DeckContextValue {
  const ctx = useContext(DeckContext);
  if (!ctx) throw new Error("useDeck must be used within <DeckProvider>");
  return ctx;
}

export function DeckProvider({
  children,
  rootRef,
  onExit,
}: {
  children: ReactNode;
  rootRef: RefObject<HTMLElement | null>;
  onExit: () => void;
}) {
  const total = SLIDE_ORDER.length;

  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1);

  const [overview, setOverviewState] = useState(false);
  const [help, setHelpState] = useState(false);
  const [notes, setNotes] = useState(false);
  const [autoplay, setAutoplay] = useState(false);
  const [laser, setLaser] = useState(false);
  const [music, setMusic] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  const [elapsedMs, setElapsedMs] = useState(0);
  const [started, setStarted] = useState(false);

  const { isFullscreen, enter, exit, toggle } = useFullscreen(rootRef);

  const start = useCallback(() => setStarted(true), []);

  const goTo = useCallback(
    (i: number) => {
      setIndex((prev) => {
        const clamped = Math.max(0, Math.min(total - 1, i));
        setDirection(clamped >= prev ? 1 : -1);
        return clamped;
      });
    },
    [total],
  );

  const next = useCallback(() => {
    setIndex((prev) => {
      setDirection(1);
      return Math.min(total - 1, prev + 1);
    });
  }, [total]);

  const prev = useCallback(() => {
    setIndex((p) => {
      setDirection(-1);
      return Math.max(0, p - 1);
    });
  }, []);

  const setOverview = useCallback((v: boolean) => setOverviewState(v), []);
  const toggleOverview = useCallback(() => setOverviewState((v) => !v), []);
  const setHelp = useCallback((v: boolean) => setHelpState(v), []);
  const toggleHelp = useCallback(() => setHelpState((v) => !v), []);
  const toggleNotes = useCallback(() => setNotes((v) => !v), []);
  const toggleAutoplay = useCallback(() => setAutoplay((v) => !v), []);
  const toggleLaser = useCallback(() => setLaser((v) => !v), []);
  const toggleMusic = useCallback(() => setMusic((v) => !v), []);
  const toggleTheme = useCallback(() => setTheme((t) => (t === "dark" ? "light" : "dark")), []);
  const resetTimer = useCallback(() => setElapsedMs(0), []);

  // Autoplay — schedule the next advance; simply stops at the last slide.
  useEffect(() => {
    if (!autoplay || index >= total - 1) return;
    const id = window.setTimeout(() => next(), AUTOPLAY_INTERVAL_MS);
    return () => window.clearTimeout(id);
  }, [autoplay, index, total, next]);

  // Presentation timer.
  useEffect(() => {
    const started = Date.now() - elapsedMs;
    const id = window.setInterval(() => setElapsedMs(Date.now() - started), 250);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo<DeckContextValue>(
    () => ({
      index,
      direction,
      total,
      slideId: SLIDE_ORDER[index],
      progress: total > 1 ? index / (total - 1) : 0,
      atStart: index === 0,
      atEnd: index === total - 1,
      goTo,
      next,
      prev,
      overview,
      toggleOverview,
      setOverview,
      help,
      toggleHelp,
      setHelp,
      notes,
      toggleNotes,
      autoplay,
      toggleAutoplay,
      laser,
      toggleLaser,
      music,
      toggleMusic,
      theme,
      toggleTheme,
      elapsedMs,
      resetTimer,
      isFullscreen,
      enterFullscreen: enter,
      exitFullscreen: exit,
      toggleFullscreen: toggle,
      started,
      start,
      exitPresentation: onExit,
    }),
    [
      index,
      direction,
      total,
      goTo,
      next,
      prev,
      overview,
      toggleOverview,
      setOverview,
      help,
      toggleHelp,
      setHelp,
      notes,
      toggleNotes,
      autoplay,
      toggleAutoplay,
      laser,
      toggleLaser,
      music,
      toggleMusic,
      theme,
      toggleTheme,
      elapsedMs,
      resetTimer,
      isFullscreen,
      enter,
      exit,
      toggle,
      started,
      start,
      onExit,
    ],
  );

  return <DeckContext.Provider value={value}>{children}</DeckContext.Provider>;
}

/** Small helper to format elapsed ms as m:ss for the timer chip. */
export function formatElapsed(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
