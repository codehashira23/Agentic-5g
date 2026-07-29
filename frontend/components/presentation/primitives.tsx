"use client";
import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { container, item, scaleIn } from "@/lib/presentation/motion";
import { Icon } from "./icons";

/**
 * Reusable slide building blocks. Every slide composes these so spacing,
 * typography and entrance animations stay consistent and premium.
 */

/** Outer layout: fills the stage, centers content, responsive padding. */
export function SlideLayout({
  children,
  className = "",
  align = "center",
}: {
  children: ReactNode;
  className?: string;
  align?: "center" | "start";
}) {
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className={`pv-slide-scroll relative z-10 flex h-full w-full flex-col ${
        align === "center" ? "justify-center" : "justify-start pt-[8vh]"
      } overflow-auto px-[6vw] py-[6vh] md:px-[9vw] ${className}`}
    >
      <div className="mx-auto w-full max-w-[1200px]">{children}</div>
    </motion.div>
  );
}

/** Small uppercase gradient label with a leading bar. */
export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <motion.div variants={item} className="mb-5 flex items-center gap-3">
      <span className="h-px w-10 bg-gradient-to-r from-ai to-transparent" />
      <span className="section-eyebrow pv-gradient-text">{children}</span>
    </motion.div>
  );
}

/** Primary slide headline. */
export function SlideHeading({
  children,
  gradient = false,
  className = "",
}: {
  children: ReactNode;
  gradient?: boolean;
  className?: string;
}) {
  return (
    <motion.h2
      variants={item}
      className={`font-display text-balance text-4xl font-bold leading-[1.08] tracking-tight md:text-6xl ${
        gradient ? "pv-gradient-text" : "text-primary"
      } ${className}`}
    >
      {children}
    </motion.h2>
  );
}

/** Supporting lead paragraph. */
export function Lead({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <motion.p
      variants={item}
      className={`max-w-3xl text-pretty text-lg leading-relaxed text-muted md:text-2xl ${className}`}
    >
      {children}
    </motion.p>
  );
}

/** Frosted glass card with hover lift. */
export function GlassCard({
  children,
  className = "",
  variant = "item",
}: {
  children: ReactNode;
  className?: string;
  variant?: "item" | "scale";
}) {
  return (
    <motion.div
      variants={variant === "scale" ? scaleIn : item}
      className={`glass card-hover-lift group relative overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-2 ${className}`}
    >
      {children}
    </motion.div>
  );
}

/** Gold-tinted icon chip used inside cards. */
export function IconBadge({
  name,
  tone = "ai",
  className = "",
}: {
  name: string;
  tone?: "ai" | "cyan";
  className?: string;
}) {
  return (
    <span
      className={`inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border ${
        tone === "cyan"
          ? "border-cyan/30 bg-cyan/10 text-cyan"
          : "border-ai/30 bg-ai/10 text-ai"
      } ${className}`}
    >
      <Icon name={name} className="h-6 w-6" />
    </span>
  );
}

/** A single feature/point card: icon + title + description. */
export function FeatureCard({
  icon,
  title,
  desc,
  tone = "ai",
}: {
  icon: string;
  title: string;
  desc: string;
  tone?: "ai" | "cyan";
}) {
  return (
    <GlassCard className="flex flex-col gap-4">
      {/* hover glow */}
      <span
        aria-hidden
        className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full bg-ai/10 opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100"
      />
      <IconBadge name={icon} tone={tone} />
      <div className="flex flex-col gap-1.5">
        <h3 className="text-lg font-semibold text-primary">{title}</h3>
        <p className="text-sm leading-relaxed text-muted">{desc}</p>
      </div>
    </GlassCard>
  );
}

/** Motion-enabled wrapper so slides can animate arbitrary blocks as items. */
export function Reveal({
  children,
  className = "",
  as = "scale",
}: {
  children: ReactNode;
  className?: string;
  as?: "item" | "scale";
}) {
  return (
    <motion.div variants={as === "scale" ? scaleIn : item} className={className}>
      {children}
    </motion.div>
  );
}
