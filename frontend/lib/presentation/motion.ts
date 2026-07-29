import type { Variants } from "framer-motion";

/** Expressive ease used across the deck (easeOutExpo-ish). */
export const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

/** Stagger parent — reveals children in sequence. */
export const container: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.09, delayChildren: 0.12 },
  },
};

/** Fade + rise for list/grid items. */
export const item: Variants = {
  hidden: { opacity: 0, y: 26 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

/** Scale-in for hero/feature emphasis. */
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.9 },
  show: { opacity: 1, scale: 1, transition: { duration: 0.65, ease: EASE } },
};

/** Simple fade. */
export const fade: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.7, ease: EASE } },
};

/** Slide-to-slide transition (direction-aware). */
export const slideVariants: Variants = {
  enter: (dir: number) => ({
    opacity: 0,
    x: dir >= 0 ? 80 : -80,
    scale: 0.98,
    filter: "blur(6px)",
  }),
  center: {
    opacity: 1,
    x: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: { duration: 0.55, ease: EASE },
  },
  exit: (dir: number) => ({
    opacity: 0,
    x: dir >= 0 ? -80 : 80,
    scale: 0.98,
    filter: "blur(6px)",
    transition: { duration: 0.4, ease: EASE },
  }),
};
