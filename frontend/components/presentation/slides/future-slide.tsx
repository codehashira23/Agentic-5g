"use client";
import { motion } from "framer-motion";
import { FUTURE } from "@/lib/presentation/config";
import { item } from "@/lib/presentation/motion";
import { Eyebrow, SlideHeading, SlideLayout } from "../primitives";
import { Icon } from "../icons";

export default function FutureSlide() {
  return (
    <SlideLayout>
      <Eyebrow>{FUTURE.eyebrow}</Eyebrow>
      <SlideHeading className="mb-9 max-w-4xl">{FUTURE.title}</SlideHeading>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {FUTURE.items.map((f) => (
          <motion.div
            key={f.title}
            variants={item}
            className="glass card-hover-lift group relative flex items-start gap-4 overflow-hidden rounded-2xl border border-border bg-card p-5"
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-cyan/25 bg-cyan/10 text-cyan">
              <Icon name={f.icon} className="h-5 w-5" />
            </span>
            <div>
              <h3 className="text-base font-semibold text-primary">{f.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-muted">{f.desc}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </SlideLayout>
  );
}
