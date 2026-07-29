"use client";
import { motion } from "framer-motion";
import { WORKFLOW } from "@/lib/presentation/config";
import { item } from "@/lib/presentation/motion";
import { Eyebrow, SlideHeading, SlideLayout } from "../primitives";
import { Icon } from "../icons";

export default function WorkflowSlide() {
  return (
    <SlideLayout>
      <Eyebrow>{WORKFLOW.eyebrow}</Eyebrow>
      <SlideHeading className="mb-10 max-w-4xl">{WORKFLOW.title}</SlideHeading>

      <div className="grid grid-cols-2 gap-x-4 gap-y-6 md:grid-cols-3 lg:grid-cols-6">
        {WORKFLOW.steps.map((step, i) => (
          <motion.div key={step.title} variants={item} className="relative flex flex-col items-center text-center">
            {/* connector line (not on last of a visual row — simple + always visible on lg) */}
            {i < WORKFLOW.steps.length - 1 && (
              <span className="absolute left-1/2 top-8 hidden h-px w-full bg-gradient-to-r from-ai/50 to-transparent lg:block" />
            )}
            <span className="relative z-10 mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-ai/30 bg-ai/10 text-ai glow-ai">
              <Icon name={step.icon} className="h-7 w-7" />
              <span className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-ai font-mono text-xs font-bold text-black">
                {i + 1}
              </span>
            </span>
            <p className="text-base font-semibold text-primary">{step.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-muted">{step.desc}</p>
          </motion.div>
        ))}
      </div>

      <motion.div
        variants={item}
        className="mt-10 flex items-center justify-center gap-2 text-sm text-faint"
      >
        <Icon name="Orbit" className="h-4 w-4 text-cyan" />
        Every cycle feeds the next — Agent5G gets smarter with each loop
      </motion.div>
    </SlideLayout>
  );
}
