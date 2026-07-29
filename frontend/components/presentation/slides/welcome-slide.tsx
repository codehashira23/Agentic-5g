"use client";
import { motion } from "framer-motion";
import { PROJECT } from "@/lib/presentation/config";
import { item, scaleIn } from "@/lib/presentation/motion";
import { SlideLayout } from "../primitives";
import { Icon } from "../icons";

export default function WelcomeSlide() {
  return (
    <SlideLayout>
      <div className="flex flex-col items-center text-center">
        {/* 5G signal rings + glowing core */}
        <motion.div
          variants={scaleIn}
          className="relative mb-9 flex h-28 w-28 items-center justify-center"
        >
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="absolute rounded-full border border-ai/50"
              style={{
                width: 56,
                height: 56,
                animation: `splash-ping 2.6s cubic-bezier(0,0,0.2,1) ${i * 0.6}s infinite`,
              }}
            />
          ))}
          <span className="relative z-10 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-ai to-cyan glow-ai">
            <Icon name="Radio" className="h-7 w-7 text-black" />
          </span>
        </motion.div>

        <motion.p variants={item} className="section-eyebrow mb-4 text-faint">
          {PROJECT.event} · {PROJECT.year}
        </motion.p>

        <motion.h1
          variants={item}
          className="font-display pv-gradient-text text-6xl font-black tracking-[0.12em] md:text-8xl"
        >
          {PROJECT.name}
        </motion.h1>

        <motion.p variants={item} className="mt-6 text-2xl font-medium text-primary md:text-3xl">
          {PROJECT.tagline}
        </motion.p>
        <motion.p variants={item} className="mt-3 max-w-2xl text-pretty text-base text-muted md:text-lg">
          {PROJECT.subtitle}
        </motion.p>

        <motion.div
          variants={item}
          className="mt-9 flex flex-wrap items-center justify-center gap-3"
        >
          <span className="glass inline-flex items-center gap-2 rounded-full border border-ai/30 px-4 py-2 text-sm font-medium text-ai">
            <Icon name="Signal" className="h-4 w-4" />
            {PROJECT.release}
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm text-muted">
            <Icon name="ArrowRight" className="h-4 w-4" />
            Press → or Space to begin
          </span>
        </motion.div>
      </div>
    </SlideLayout>
  );
}
