"use client";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { CLOSING, PROJECT, TEAM } from "@/lib/presentation/config";
import { item, scaleIn } from "@/lib/presentation/motion";
import { fireConfetti } from "@/lib/presentation/confetti";
import { Eyebrow, SlideLayout } from "../primitives";
import { Icon } from "../icons";
import { QrCode } from "../qr";

export default function ThanksSlide() {
  // Celebrate when the closing slide appears.
  useEffect(() => {
    const id = window.setTimeout(() => void fireConfetti(), 260);
    return () => window.clearTimeout(id);
  }, []);

  return (
    <SlideLayout>
      <div className="flex flex-col items-center text-center">
        <Eyebrow>{CLOSING.eyebrow}</Eyebrow>

        <motion.h2
          variants={item}
          className="font-display pv-gradient-text text-6xl font-black tracking-tight md:text-8xl"
        >
          {CLOSING.title}
        </motion.h2>
        <motion.p variants={item} className="mt-4 text-lg text-muted md:text-xl">
          {CLOSING.subtitle}
        </motion.p>

        <motion.div variants={scaleIn} className="mt-9 flex flex-col items-center gap-3">
          <QrCode value={PROJECT.github} />
          <p className="text-xs uppercase tracking-widest text-faint">{CLOSING.qrCaption}</p>
        </motion.div>

        <motion.div
          variants={item}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <a
            href={PROJECT.github}
            target="_blank"
            rel="noopener noreferrer"
            className="glass inline-flex items-center gap-2 rounded-full border border-border px-5 py-2.5 text-sm font-medium text-primary transition-colors hover:border-ai/40 hover:text-ai"
          >
            <Icon name="Github" className="h-4 w-4" />
            {PROJECT.github.replace("https://", "")}
          </a>
          <a
            href={PROJECT.brochureUrl}
            download="Agent5G-Brochure.pdf"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-ai to-cyan px-5 py-2.5 text-sm font-semibold text-black transition-transform hover:scale-[1.03]"
          >
            <Icon name="Download" className="h-4 w-4" />
            Download brochure
          </a>
        </motion.div>

        <motion.p variants={item} className="mt-8 text-sm text-faint">
          {PROJECT.fullName} · {TEAM.collegeShort} · {PROJECT.year}
        </motion.p>
      </div>
    </SlideLayout>
  );
}
