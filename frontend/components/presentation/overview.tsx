"use client";
import { AnimatePresence, motion } from "framer-motion";
import { SLIDE_ORDER } from "@/lib/presentation/config";
import { useDeck } from "@/lib/presentation/deck-context";
import { SLIDES } from "./slide-registry";
import { Icon } from "./icons";

/**
 * Mini overview mode — a grid of every slide. Click a card (or press its
 * number) to jump straight there. Toggled with O.
 */
export function Overview() {
  const { overview, setOverview, goTo, index } = useDeck();

  return (
    <AnimatePresence>
      {overview && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 z-[10030] overflow-auto bg-black/80 backdrop-blur-md"
        >
          <div className="mx-auto max-w-6xl px-6 py-10">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="font-display flex items-center gap-2 text-xl font-bold text-primary">
                <Icon name="Blocks" className="h-5 w-5 text-ai" />
                Overview
              </h3>
              <button
                type="button"
                onClick={() => setOverview(false)}
                className="rounded-lg border border-border px-3 py-1.5 text-sm text-muted transition-colors hover:border-ai/40 hover:text-ai"
              >
                Close
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {SLIDE_ORDER.map((id, i) => {
                const meta = SLIDES[id];
                const active = i === index;
                return (
                  <motion.button
                    key={id}
                    type="button"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    onClick={() => {
                      goTo(i);
                      setOverview(false);
                    }}
                    className={`group relative flex aspect-video flex-col justify-between overflow-hidden rounded-xl border p-4 text-left transition-all ${
                      active
                        ? "border-ai bg-ai/10 glow-ai"
                        : "border-border bg-card hover:border-ai/40 hover:bg-card-hover"
                    }`}
                  >
                    <span className="font-mono text-xs text-faint">
                      {String(i + 1).padStart(2, "0")} / {SLIDE_ORDER.length}
                    </span>
                    <span
                      className={`font-display text-lg font-bold ${active ? "text-ai" : "text-primary"}`}
                    >
                      {meta.title}
                    </span>
                    <span className="absolute right-3 top-3 h-2 w-2 rounded-full bg-ai opacity-0 transition-opacity group-hover:opacity-100" />
                  </motion.button>
                );
              })}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
