"use client";
import { AnimatePresence, motion } from "framer-motion";
import { useDeck } from "@/lib/presentation/deck-context";
import { SLIDES } from "./slide-registry";
import { Icon } from "./icons";

/** Docked presenter notes for the current slide (toggle with N). */
export function PresenterNotes() {
  const { notes, slideId, index, total } = useDeck();
  const meta = SLIDES[slideId];

  return (
    <AnimatePresence>
      {notes && (
        <motion.aside
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          transition={{ type: "spring", stiffness: 240, damping: 26 }}
          className="glass absolute bottom-20 left-4 z-[10022] w-[min(90vw,420px)] rounded-2xl border border-ai/25 bg-panel p-5 shadow-2 md:left-6"
        >
          <div className="mb-2 flex items-center gap-2">
            <Icon name="ClipboardList" className="h-4 w-4 text-ai" />
            <span className="section-eyebrow text-ai">Presenter notes</span>
            <span className="ml-auto font-mono text-xs text-faint">
              {index + 1}/{total} · {meta.title}
            </span>
          </div>
          <p className="text-sm leading-relaxed text-muted">{meta.notes}</p>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
