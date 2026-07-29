"use client";
import { motion } from "framer-motion";
import { TEAM } from "@/lib/presentation/config";
import { item, scaleIn } from "@/lib/presentation/motion";
import { Eyebrow, SlideHeading, SlideLayout } from "../primitives";
import { Icon } from "../icons";

export default function TeamSlide() {
  return (
    <SlideLayout>
      <div className="flex flex-col items-center text-center">
        <Eyebrow>Team</Eyebrow>
        <SlideHeading className="mb-10">Built by</SlideHeading>

        <div className="flex flex-wrap items-stretch justify-center gap-5">
          {TEAM.members.map((m) => (
            <motion.div
              key={m.roll}
              variants={scaleIn}
              className="glass card-hover-lift flex w-72 flex-col items-center gap-4 rounded-3xl border border-border bg-card p-8"
            >
              <span className="relative flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-ai to-cyan text-3xl font-black text-black glow-ai">
                {m.initials}
              </span>
              <div>
                <p className="font-display text-xl font-bold tracking-wide text-primary">{m.name}</p>
                <p className="mt-1 font-mono text-sm text-ai">{m.roll}</p>
                <p className="mt-2 text-sm text-muted">{m.role}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          variants={item}
          className="mt-9 flex flex-col items-center gap-3 sm:flex-row sm:gap-8"
        >
          <span className="inline-flex items-center gap-2 text-sm text-muted">
            <Icon name="GraduationCap" className="h-4 w-4 text-ai" />
            Mentor: <span className="font-medium text-primary">{TEAM.mentor}</span>
          </span>
          <span className="inline-flex items-center gap-2 text-sm text-muted">
            <Icon name="Aperture" className="h-4 w-4 text-cyan" />
            {TEAM.college}
          </span>
        </motion.div>
      </div>
    </SlideLayout>
  );
}
