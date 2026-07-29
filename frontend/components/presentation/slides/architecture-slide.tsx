"use client";
import { motion } from "framer-motion";
import { ARCHITECTURE } from "@/lib/presentation/config";
import { item } from "@/lib/presentation/motion";
import { Eyebrow, IconBadge, SlideHeading, SlideLayout } from "../primitives";
import { Icon } from "../icons";

export default function ArchitectureSlide() {
  return (
    <SlideLayout>
      <Eyebrow>{ARCHITECTURE.eyebrow}</Eyebrow>
      <SlideHeading className="mb-9 max-w-4xl">{ARCHITECTURE.title}</SlideHeading>

      <div className="relative flex flex-col gap-3">
        {ARCHITECTURE.layers.map((layer, i) => (
          <motion.div
            key={layer.name}
            variants={item}
            className="glass card-hover-lift relative flex items-center gap-5 overflow-hidden rounded-2xl border border-border bg-card px-5 py-4"
          >
            {/* left tone accent */}
            <span
              className={`absolute inset-y-0 left-0 w-1 ${
                layer.tone === "cyan" ? "bg-cyan/70" : "bg-ai/70"
              }`}
            />
            <IconBadge name={layer.icon} tone={layer.tone as "ai" | "cyan"} />
            <div className="min-w-0 flex-1">
              <p className="text-lg font-semibold text-primary">{layer.name}</p>
              <p className="text-sm text-muted">{layer.desc}</p>
            </div>
            <span className="hidden shrink-0 font-mono text-xs text-faint md:block">
              L{ARCHITECTURE.layers.length - i}
            </span>
          </motion.div>
        ))}

        {/* closed-loop hint */}
        <motion.div
          variants={item}
          className="mt-2 flex items-center justify-center gap-2 text-sm text-faint"
        >
          <Icon name="Waypoints" className="h-4 w-4 text-ai" />
          Telemetry flows up · autonomous actions flow back down — a continuous closed loop
        </motion.div>
      </div>
    </SlideLayout>
  );
}
