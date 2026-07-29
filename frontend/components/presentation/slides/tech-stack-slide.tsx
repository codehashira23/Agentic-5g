"use client";
import { motion } from "framer-motion";
import { TECH_STACK } from "@/lib/presentation/config";
import { item } from "@/lib/presentation/motion";
import { Eyebrow, IconBadge, SlideHeading, SlideLayout } from "../primitives";

export default function TechStackSlide() {
  const allTech = TECH_STACK.groups.flatMap((g) => g.items.map((i) => i.name));

  return (
    <SlideLayout>
      <Eyebrow>{TECH_STACK.eyebrow}</Eyebrow>
      <SlideHeading className="mb-8 max-w-4xl">{TECH_STACK.title}</SlideHeading>

      <div className="grid gap-4 sm:grid-cols-2">
        {TECH_STACK.groups.map((group) => (
          <motion.div
            key={group.label}
            variants={item}
            className="glass card-hover-lift rounded-2xl border border-border bg-card p-5"
          >
            <div className="mb-4 flex items-center gap-3">
              <IconBadge name={group.icon} />
              <h3 className="text-base font-semibold text-primary">{group.label}</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {group.items.map((t) => (
                <span
                  key={t.name}
                  className="rounded-full border border-border bg-white/[0.03] px-3 py-1 text-sm text-muted transition-colors hover:border-ai/40 hover:text-ai"
                >
                  {t.name}
                </span>
              ))}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Infinite marquee ticker of the whole stack */}
      <motion.div
        variants={item}
        className="relative mt-8 overflow-hidden rounded-full border border-border bg-white/[0.02] py-3"
      >
        <div className="pv-marquee-track whitespace-nowrap px-4 font-mono text-sm text-faint">
          {[...allTech, ...allTech].map((t, i) => (
            <span key={i} className="mx-2 inline-flex items-center gap-2">
              <span className="text-ai">◇</span>
              {t}
            </span>
          ))}
        </div>
      </motion.div>
    </SlideLayout>
  );
}
