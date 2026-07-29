"use client";
import { motion } from "framer-motion";
import { FEATURES } from "@/lib/presentation/config";
import { item } from "@/lib/presentation/motion";
import { Eyebrow, SlideHeading, SlideLayout } from "../primitives";
import { Icon } from "../icons";

export default function FeaturesSlide() {
  return (
    <SlideLayout>
      <Eyebrow>{FEATURES.eyebrow}</Eyebrow>
      <SlideHeading className="mb-8 max-w-4xl">{FEATURES.title}</SlideHeading>

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-3 lg:grid-cols-4">
        {FEATURES.items.map((f) => (
          <motion.div
            key={f.title}
            variants={item}
            className="glass card-hover-lift group flex flex-col gap-2.5 rounded-xl border border-border bg-card p-4"
          >
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-ai/25 bg-ai/10 text-ai transition-colors group-hover:bg-ai/20">
              <Icon name={f.icon} className="h-5 w-5" />
            </span>
            <p className="text-sm font-semibold text-primary">{f.title}</p>
            <p className="text-xs leading-relaxed text-muted">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </SlideLayout>
  );
}
