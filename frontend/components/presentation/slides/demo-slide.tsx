"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { DEMO } from "@/lib/presentation/config";
import { item } from "@/lib/presentation/motion";
import { Eyebrow, SlideHeading, SlideLayout } from "../primitives";
import { Icon } from "../icons";

export default function DemoSlide() {
  const [loaded, setLoaded] = useState(false);

  return (
    <SlideLayout>
      <Eyebrow>{DEMO.eyebrow}</Eyebrow>
      <SlideHeading className="mb-8 max-w-4xl">{DEMO.title}</SlideHeading>

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_1.15fr]">
        {/* Demo script */}
        <div className="flex flex-col gap-3">
          {DEMO.script.map((s, i) => (
            <motion.div
              key={s.label}
              variants={item}
              className="glass flex items-center gap-4 rounded-xl border border-border bg-card px-4 py-3"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-ai/25 bg-ai/10 text-ai">
                <Icon name={s.icon} className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-primary">
                  <span className="mr-2 font-mono text-ai">{i + 1}.</span>
                  {s.label}
                </p>
                <p className="text-xs text-muted">{s.detail}</p>
              </div>
            </motion.div>
          ))}
          <motion.p variants={item} className="mt-1 text-xs text-faint">
            {DEMO.hint}
          </motion.p>
        </div>

        {/* Embedded live app in a browser frame */}
        <motion.div
          variants={item}
          className="glass overflow-hidden rounded-2xl border border-border bg-card shadow-2"
        >
          <div className="flex items-center gap-2 border-b border-border bg-white/[0.03] px-4 py-2.5">
            <span className="h-3 w-3 rounded-full bg-crit/70" />
            <span className="h-3 w-3 rounded-full bg-warn/70" />
            <span className="h-3 w-3 rounded-full bg-ok/70" />
            <span className="ml-3 flex-1 truncate rounded-md bg-black/30 px-3 py-1 font-mono text-xs text-faint">
              localhost:3000/dashboard
            </span>
          </div>
          <div className="relative aspect-[16/10] w-full">
            {loaded ? (
              <iframe
                src="/dashboard"
                title="Agent5G live dashboard"
                className="h-full w-full border-0 bg-base"
                loading="lazy"
              />
            ) : (
              <button
                type="button"
                onClick={() => setLoaded(true)}
                className="group flex h-full w-full flex-col items-center justify-center gap-3 bg-gradient-to-br from-ai/5 to-transparent transition-colors hover:from-ai/10"
              >
                <span className="flex h-14 w-14 items-center justify-center rounded-full border border-ai/40 bg-ai/10 text-ai transition-transform group-hover:scale-110 glow-ai">
                  <Icon name="Play" className="h-6 w-6" />
                </span>
                <span className="text-sm font-medium text-primary">Load live dashboard</span>
                <span className="text-xs text-faint">Embeds the running app inside the deck</span>
              </button>
            )}
          </div>
        </motion.div>
      </div>
    </SlideLayout>
  );
}
