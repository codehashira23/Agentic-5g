"use client";
import { Fragment, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  ArrowDown,
  Check,
  ChevronRight,
  Copy,
  Info,
  Lightbulb,
  MessageCircleQuestion,
  ShieldAlert,
} from "lucide-react";

/**
 * Reusable documentation primitives for the hidden /internal docs.
 * Presentational, theme-aware building blocks (headings with anchor ids,
 * copyable code, callouts, diagrams, flows, tables, collapsibles, Q&A).
 */

/* --------------------------------------------------------------- typography */
export function H2({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2
      id={id}
      className="scroll-mt-8 font-display mt-14 mb-4 text-2xl font-bold tracking-tight text-primary first:mt-0 md:text-3xl"
    >
      {children}
    </h2>
  );
}

export function H3({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h3 id={id} className="scroll-mt-8 mt-9 mb-3 text-lg font-semibold text-primary">
      {children}
    </h3>
  );
}

export function P({ children }: { children: ReactNode }) {
  return <p className="mb-4 text-[15px] leading-7 text-muted">{children}</p>;
}

export function Lead({ children }: { children: ReactNode }) {
  return <p className="mb-6 text-lg leading-8 text-muted">{children}</p>;
}

/** Inline code. */
export function C({ children }: { children: ReactNode }) {
  return (
    <code className="rounded border border-border bg-white/[0.05] px-1.5 py-0.5 font-mono text-[12.5px] text-cyan">
      {children}
    </code>
  );
}

export function Ul({ children }: { children: ReactNode }) {
  return <ul className="mb-5 flex flex-col gap-2 text-[15px] leading-7 text-muted">{children}</ul>;
}

export function Li({ children }: { children: ReactNode }) {
  return (
    <li className="relative pl-5 before:absolute before:left-0 before:top-[0.6em] before:h-1.5 before:w-1.5 before:rounded-full before:bg-ai/70">
      {children}
    </li>
  );
}

/* --------------------------------------------------------------- code block */
export function CodeBlock({
  code,
  lang = "ts",
  title,
}: {
  code: string;
  lang?: string;
  title?: string;
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked */
    }
  };
  return (
    <div className="my-5 overflow-hidden rounded-xl border border-border bg-[#080b12]">
      <div className="flex items-center justify-between border-b border-border bg-white/[0.02] px-4 py-2">
        <span className="font-mono text-xs text-faint">{title ?? lang}</span>
        <button
          type="button"
          onClick={copy}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-faint transition-colors hover:bg-card-hover hover:text-primary"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-ok" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="pv-slide-scroll overflow-auto p-4 text-[13px] leading-6">
        <code className="whitespace-pre font-mono text-primary">{code}</code>
      </pre>
    </div>
  );
}

/* ----------------------------------------------------------------- callout */
const CALLOUT = {
  info: { Icon: Info, cls: "border-info/30 bg-info/[0.07]", icon: "text-info" },
  tip: { Icon: Lightbulb, cls: "border-ai/30 bg-ai/[0.07]", icon: "text-ai" },
  warn: { Icon: AlertTriangle, cls: "border-warn/30 bg-warn/[0.07]", icon: "text-warn" },
  danger: { Icon: ShieldAlert, cls: "border-crit/30 bg-crit/[0.07]", icon: "text-crit" },
} as const;

export function Callout({
  type = "info",
  title,
  children,
}: {
  type?: keyof typeof CALLOUT;
  title?: string;
  children: ReactNode;
}) {
  const cfg = CALLOUT[type];
  return (
    <div className={`my-5 flex gap-3 rounded-xl border p-4 ${cfg.cls}`}>
      <cfg.Icon className={`mt-0.5 h-5 w-5 shrink-0 ${cfg.icon}`} />
      <div className="text-sm leading-7 text-muted">
        {title && <p className="mb-1 font-semibold text-primary">{title}</p>}
        {children}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- diagram */
/** Preformatted ASCII/box diagram (horizontally scrollable). */
export function Diagram({ children, caption }: { children: ReactNode; caption?: string }) {
  return (
    <figure className="my-6">
      <pre className="pv-slide-scroll overflow-auto rounded-xl border border-border bg-[#080b12] p-5 font-mono text-[12.5px] leading-5 text-muted">
        {children}
      </pre>
      {caption && <figcaption className="mt-2 text-center text-xs text-faint">{caption}</figcaption>}
    </figure>
  );
}

/** Vertical flow of steps connected by arrows. */
export function Flow({ steps }: { steps: { label: string; sub?: string; tone?: "ai" | "cyan" }[] }) {
  return (
    <div className="my-6 flex flex-col items-center">
      {steps.map((s, i) => (
        <Fragment key={i}>
          <div
            className={`glass w-full max-w-md rounded-xl border px-4 py-3 text-center ${
              s.tone === "cyan" ? "border-cyan/30" : "border-border"
            }`}
          >
            <p className="text-sm font-semibold text-primary">{s.label}</p>
            {s.sub && <p className="mt-0.5 text-xs text-faint">{s.sub}</p>}
          </div>
          {i < steps.length - 1 && <ArrowDown className="my-1.5 h-4 w-4 shrink-0 text-ai/70" />}
        </Fragment>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------- table */
export function Table({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="pv-slide-scroll my-5 overflow-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="bg-white/[0.03]">
            {head.map((h) => (
              <th key={h} className="border-b border-border px-4 py-2.5 font-semibold text-primary">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border/60 last:border-0 hover:bg-white/[0.02]">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2.5 align-top text-muted">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Definition list — used for file overviews (path / purpose / imported-by …). */
export function KeyValue({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="my-4 grid grid-cols-[130px_1fr] gap-x-4 gap-y-2.5 text-sm">
      {items.map(([k, v], i) => (
        <Fragment key={i}>
          <dt className="text-faint">{k}</dt>
          <dd className="text-muted">{v}</dd>
        </Fragment>
      ))}
    </dl>
  );
}

export function Pill({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "ai" | "cyan" }) {
  const cls =
    tone === "ai"
      ? "border-ai/30 bg-ai/10 text-ai"
      : tone === "cyan"
        ? "border-cyan/30 bg-cyan/10 text-cyan"
        : "border-border bg-white/[0.03] text-muted";
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {children}
    </span>
  );
}

/* ------------------------------------------------------------- collapsible */
export function Collapsible({
  title,
  children,
  defaultOpen = false,
}: {
  title: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="my-2.5 overflow-hidden rounded-xl border border-border bg-card/40">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2.5 px-4 py-3 text-left transition-colors hover:bg-card-hover"
      >
        <ChevronRight className={`h-4 w-4 shrink-0 text-ai transition-transform ${open ? "rotate-90" : ""}`} />
        <span className="flex-1">{title}</span>
      </button>
      {open && <div className="border-t border-border px-4 py-3.5">{children}</div>}
    </div>
  );
}

/** Interview-style Q&A — each question expands to reveal the answer. */
export function InterviewQA({ items }: { items: { q: string; a: ReactNode }[] }) {
  return (
    <div className="my-5">
      <p className="section-eyebrow mb-3 flex items-center gap-2 text-ai">
        <MessageCircleQuestion className="h-4 w-4" />
        Interview questions
      </p>
      <div className="flex flex-col gap-2">
        {items.map((item, i) => (
          <Collapsible
            key={i}
            title={
              <span className="text-sm font-medium text-primary">
                <span className="mr-2 font-mono text-ai">Q{i + 1}</span>
                {item.q}
              </span>
            }
          >
            <div className="text-sm leading-7 text-muted">{item.a}</div>
          </Collapsible>
        ))}
      </div>
    </div>
  );
}

/** Header for a file walkthrough: monospace path + tech pills. */
export function FileHeader({ path, tech }: { path: string; tech?: string[] }) {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <code className="rounded-md border border-ai/25 bg-ai/[0.06] px-2 py-1 font-mono text-[13px] text-ai">
        {path}
      </code>
      {tech?.map((t) => (
        <Pill key={t}>{t}</Pill>
      ))}
    </div>
  );
}
