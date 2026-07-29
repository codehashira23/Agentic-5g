"use client";
import { motion } from "framer-motion";

/**
 * Persistent, GPU-accelerated background layers shared by every slide:
 * aurora ribbons, floating blobs, a masked moving grid and a spotlight sweep.
 * Rendered once by the deck (not per slide) so animations never restart and
 * transitions stay buttery. `parallax` shifts subtly as slides advance.
 */
export function Backgrounds({ parallax = 0 }: { parallax?: number }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Aurora ribbons */}
      <div
        className="pv-aurora pv-aurora-1"
        style={{
          top: "-14%",
          left: "-6%",
          width: "46vw",
          height: "46vw",
          background:
            "radial-gradient(circle, color-mix(in srgb, var(--accent-ai) 60%, transparent), transparent 70%)",
        }}
      />
      <div
        className="pv-aurora pv-aurora-2"
        style={{
          top: "-8%",
          right: "-8%",
          width: "40vw",
          height: "40vw",
          background:
            "radial-gradient(circle, color-mix(in srgb, #4f83cc 55%, transparent), transparent 70%)",
        }}
      />
      <div
        className="pv-aurora pv-aurora-3"
        style={{
          bottom: "-18%",
          left: "24%",
          width: "48vw",
          height: "38vw",
          background:
            "radial-gradient(circle, color-mix(in srgb, var(--accent-cyan) 45%, transparent), transparent 72%)",
        }}
      />

      {/* Parallax blob layer */}
      <motion.div
        className="absolute inset-0"
        animate={{ x: parallax * -22, y: parallax * -10 }}
        transition={{ type: "spring", stiffness: 40, damping: 20 }}
      >
        <div
          className="pv-blob"
          style={{
            top: "58%",
            left: "8%",
            width: "18vw",
            height: "18vw",
            background: "color-mix(in srgb, var(--accent-ai) 28%, transparent)",
            animationDelay: "-3s",
          }}
        />
        <div
          className="pv-blob"
          style={{
            top: "12%",
            right: "16%",
            width: "14vw",
            height: "14vw",
            background: "color-mix(in srgb, #4f83cc 30%, transparent)",
            animationDelay: "-7s",
          }}
        />
      </motion.div>

      {/* Masked moving grid */}
      <div className="pv-grid" />

      {/* Spotlight sweep from the top */}
      <div className="pv-spotlight" />

      {/* Vignette to focus the center */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 120% at 50% 40%, transparent 55%, color-mix(in srgb, var(--bg-base) 82%, transparent) 100%)",
        }}
      />
    </div>
  );
}
