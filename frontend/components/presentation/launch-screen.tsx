"use client";
import { AnimatePresence, motion } from "framer-motion";
import { PROJECT } from "@/lib/presentation/config";
import { useDeck } from "@/lib/presentation/deck-context";
import { EASE } from "@/lib/presentation/motion";
import { Icon } from "./icons";

/**
 * Elegant pre-deck launch overlay. "Start Presentation" enters browser
 * fullscreen (a real user gesture) and reveals the deck; a secondary option
 * starts without fullscreen. Fades away once the presentation begins.
 */
export function LaunchScreen() {
  const { started, start, enterFullscreen } = useDeck();

  const begin = (fullscreen: boolean) => {
    if (fullscreen) enterFullscreen();
    start();
  };

  return (
    <AnimatePresence>
      {!started && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.05 }}
          transition={{ duration: 0.6, ease: EASE }}
          className="absolute inset-0 z-[10010] flex flex-col items-center justify-center gap-7 bg-base/70 px-6 text-center backdrop-blur-2xl"
        >
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE }}
            className="flex flex-col items-center gap-3"
          >
            <span className="section-eyebrow text-faint">Presentation Mode</span>
            <h1 className="font-display pv-gradient-text text-5xl font-black tracking-[0.12em] md:text-7xl">
              {PROJECT.name}
            </h1>
            <p className="max-w-xl text-pretty text-base text-muted md:text-lg">
              {PROJECT.tagline} — {PROJECT.subtitle}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE, delay: 0.15 }}
            className="flex flex-col items-center gap-4"
          >
            <button
              type="button"
              onClick={() => begin(true)}
              className="group inline-flex items-center gap-3 rounded-full bg-gradient-to-r from-ai to-cyan px-8 py-4 text-lg font-semibold text-black shadow-2 transition-transform hover:scale-[1.04] focus-visible:scale-[1.04]"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-black/15">
                <Icon name="Play" className="h-4 w-4" />
              </span>
              Start Presentation
              <Icon name="ArrowRight" className="h-5 w-5 transition-transform group-hover:translate-x-1" />
            </button>

            <button
              type="button"
              onClick={() => begin(false)}
              className="text-sm text-faint underline-offset-4 transition-colors hover:text-muted hover:underline"
            >
              Enter without fullscreen
            </button>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="mt-2 flex flex-wrap items-center justify-center gap-2 text-xs text-faint"
          >
            <kbd className="rounded border border-border bg-white/[0.04] px-1.5 py-0.5 font-mono">→</kbd>
            /
            <kbd className="rounded border border-border bg-white/[0.04] px-1.5 py-0.5 font-mono">Space</kbd>
            to advance ·
            <kbd className="rounded border border-border bg-white/[0.04] px-1.5 py-0.5 font-mono">H</kbd>
            for shortcuts ·
            <kbd className="rounded border border-border bg-white/[0.04] px-1.5 py-0.5 font-mono">Esc</kbd>
            to exit
          </motion.p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
