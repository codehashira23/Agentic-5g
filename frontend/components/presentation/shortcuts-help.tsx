"use client";
import { AnimatePresence, motion } from "framer-motion";
import { useDeck } from "@/lib/presentation/deck-context";
import { Icon } from "./icons";

const SHORTCUTS: { keys: string[]; label: string }[] = [
  { keys: ["→", "Space", "PgDn"], label: "Next slide" },
  { keys: ["←", "PgUp"], label: "Previous slide" },
  { keys: ["Scroll"], label: "Navigate slides" },
  { keys: ["Home", "End"], label: "First / last slide" },
  { keys: ["F"], label: "Toggle fullscreen" },
  { keys: ["O"], label: "Overview grid" },
  { keys: ["A"], label: "Autoplay" },
  { keys: ["N"], label: "Presenter notes" },
  { keys: ["L"], label: "Laser pointer" },
  { keys: ["M"], label: "Background music" },
  { keys: ["T"], label: "Light / dark theme" },
  { keys: ["H", "?"], label: "Show / hide this help" },
  { keys: ["Esc"], label: "Exit fullscreen / close / leave" },
];

export function ShortcutsHelp() {
  const { help, setHelp } = useDeck();

  return (
    <AnimatePresence>
      {help && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 z-[10040] flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setHelp(false)}
        >
          <motion.div
            initial={{ scale: 0.92, y: 20, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.92, y: 20, opacity: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 24 }}
            className="glass w-[min(92vw,560px)] rounded-2xl border border-border bg-panel p-6 shadow-2"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-5 flex items-center justify-between">
              <h3 className="font-display flex items-center gap-2 text-lg font-bold text-primary">
                <Icon name="Signal" className="h-5 w-5 text-ai" />
                Keyboard shortcuts
              </h3>
              <button
                type="button"
                onClick={() => setHelp(false)}
                aria-label="Close help"
                className="rounded-lg p-1.5 text-faint transition-colors hover:bg-card-hover hover:text-primary"
              >
                <Icon name="ArrowRight" className="h-4 w-4 rotate-45" />
              </button>
            </div>
            <ul className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {SHORTCUTS.map((s) => (
                <li key={s.label} className="flex items-center justify-between gap-3">
                  <span className="text-sm text-muted">{s.label}</span>
                  <span className="flex flex-wrap justify-end gap-1">
                    {s.keys.map((k) => (
                      <kbd
                        key={k}
                        className="rounded-md border border-border bg-white/[0.04] px-2 py-0.5 font-mono text-xs text-primary"
                      >
                        {k}
                      </kbd>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-5 text-center text-xs text-faint">Press H or ? to toggle this panel</p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
