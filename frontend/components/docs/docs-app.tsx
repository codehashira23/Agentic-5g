"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Maximize, Minimize, Presentation, Radio, X } from "lucide-react";
import { SECTIONS } from "@/lib/docs/registry";
import { useFullscreen } from "@/lib/presentation/use-fullscreen";
import { Sidebar } from "./sidebar";
import { Toc } from "./toc";

export function DocsApp() {
  const router = useRouter();
  const rootRef = useRef<HTMLDivElement>(null);
  const mainRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const [activeId, setActiveId] = useState(SECTIONS[0].id);
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"contents" | "files">("contents");
  const [presenting, setPresenting] = useState(false);
  const [activeHeading, setActiveHeading] = useState<string | null>(SECTIONS[0].toc[0]?.id ?? null);
  const [progress, setProgress] = useState(0);

  const { isFullscreen, enter, exit, toggle } = useFullscreen(rootRef);

  const idx = SECTIONS.findIndex((s) => s.id === activeId);
  const section = SECTIONS[idx];
  const prev = idx > 0 ? SECTIONS[idx - 1] : null;
  const next = idx < SECTIONS.length - 1 ? SECTIONS[idx + 1] : null;
  const Body = section.Body;

  const selectSection = useCallback((id: string) => {
    setActiveId(id);
    setProgress(0);
    const s = SECTIONS.find((x) => x.id === id);
    setActiveHeading(s?.toc[0]?.id ?? null);
    if (mainRef.current) mainRef.current.scrollTop = 0;
  }, []);
  const goNext = useCallback(() => {
    if (next) selectSection(next.id);
  }, [next, selectSection]);
  const goPrev = useCallback(() => {
    if (prev) selectSection(prev.id);
  }, [prev, selectSection]);

  const togglePresent = useCallback(() => {
    setPresenting((p) => {
      const nextVal = !p;
      if (nextVal) void enter();
      else void exit();
      return nextVal;
    });
  }, [enter, exit]);

  const leave = useCallback(() => {
    void exit();
    router.push("/dashboard");
  }, [exit, router]);

  // Keyboard navigation.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      const typing = !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);

      if (e.key === "Escape") {
        if (presenting) {
          e.preventDefault();
          setPresenting(false);
          void exit();
        } else if (typing) {
          (el as HTMLInputElement).blur();
        } else {
          leave();
        }
        return;
      }
      if (typing) return;
      if (e.key === "/") {
        e.preventDefault();
        searchRef.current?.focus();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === " " && presenting) {
        e.preventDefault();
        goNext();
      } else if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        togglePresent();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [presenting, goNext, goPrev, togglePresent, exit, leave]);

  // Reading progress + scroll-spy.
  const onScroll = () => {
    const el = mainRef.current;
    if (!el) return;
    const max = el.scrollHeight - el.clientHeight;
    setProgress(max > 0 ? Math.min(1, el.scrollTop / max) : 0);
    const top = el.getBoundingClientRect().top;
    let current = section.toc[0]?.id ?? null;
    for (const t of section.toc) {
      const h = document.getElementById(t.id);
      if (h && h.getBoundingClientRect().top - top <= 96) current = t.id;
    }
    setActiveHeading(current);
  };

  const jump = (hid: string) =>
    document.getElementById(hid)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div
      ref={rootRef}
      className="fixed inset-0 z-[10000] flex flex-col bg-base text-primary"
      style={{
        backgroundImage:
          "radial-gradient(900px circle at 15% -10%, color-mix(in srgb, var(--accent-ai) 8%, transparent), transparent 45%)",
      }}
    >
      {/* Top bar */}
      <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-border bg-panel/70 px-4 backdrop-blur-xl">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-ai/40 bg-gradient-to-br from-ai/30 to-cyan/20 glow-ai">
            <Radio className="h-3.5 w-3.5 text-cyan" />
          </span>
          <div className="flex min-w-0 items-center gap-2">
            <span className="font-display brand-gradient text-sm font-extrabold tracking-wider">AGENT5G</span>
            <span className="text-sm text-faint">Docs</span>
            <span className="hidden rounded-full border border-border px-2 py-0.5 text-[10px] uppercase tracking-widest text-faint sm:inline">
              Internal
            </span>
          </div>
          {/* Breadcrumb */}
          <nav className="ml-2 hidden min-w-0 items-center gap-1.5 truncate text-xs text-faint md:flex">
            <span>/</span>
            <span className="text-muted">{section.group}</span>
            <span>/</span>
            <span className="truncate text-primary">{section.title}</span>
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={togglePresent}
            title="Presentation mode (F)"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-ai/40 hover:text-ai"
          >
            <Presentation className="h-4 w-4" />
            <span className="hidden sm:inline">Present</span>
          </button>
          <button
            type="button"
            onClick={toggle}
            title="Toggle fullscreen"
            className="btn-icon"
          >
            {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
          </button>
          <button type="button" onClick={leave} title="Exit docs (Esc)" className="btn-icon">
            <X className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex min-h-0 flex-1">
        {!presenting && (
          <div className="hidden md:flex">
            <Sidebar
              ref={searchRef}
              activeId={activeId}
              query={query}
              setQuery={setQuery}
              tab={tab}
              setTab={setTab}
              onSelect={selectSection}
            />
          </div>
        )}

        {/* Main content */}
        <main ref={mainRef} onScroll={onScroll} className="relative flex-1 overflow-y-auto">
          {/* Reading progress */}
          <div className="sticky top-0 z-20 h-0.5 bg-transparent">
            <div className="h-full bg-gradient-to-r from-ai to-cyan transition-[width] duration-150" style={{ width: `${progress * 100}%` }} />
          </div>

          {presenting && (
            <div className="flex items-center justify-between px-8 pt-6 text-xs text-faint">
              <span className="section-eyebrow text-ai">{section.group}</span>
              <span className="font-mono">
                {String(idx + 1).padStart(2, "0")} / {String(SECTIONS.length).padStart(2, "0")}
              </span>
            </div>
          )}

          <article className={`mx-auto px-6 pb-24 ${presenting ? "max-w-4xl pt-8 md:px-10" : "max-w-3xl pt-10"}`}>
            <div className={presenting ? "text-[1.03rem] leading-relaxed" : ""}>
              <Body />
            </div>

            {/* Prev / next */}
            <div className="mt-16 grid grid-cols-2 gap-4 border-t border-border pt-6">
              {prev ? (
                <button
                  type="button"
                  onClick={() => selectSection(prev.id)}
                  className="group flex flex-col items-start gap-1 rounded-xl border border-border p-4 text-left transition-colors hover:border-ai/40"
                >
                  <span className="inline-flex items-center gap-1 text-xs text-faint">
                    <ArrowLeft className="h-3.5 w-3.5" /> Previous
                  </span>
                  <span className="text-sm font-medium text-primary group-hover:text-ai">{prev.title}</span>
                </button>
              ) : (
                <span />
              )}
              {next ? (
                <button
                  type="button"
                  onClick={() => selectSection(next.id)}
                  className="group flex flex-col items-end gap-1 rounded-xl border border-border p-4 text-right transition-colors hover:border-ai/40"
                >
                  <span className="inline-flex items-center gap-1 text-xs text-faint">
                    Next <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                  <span className="text-sm font-medium text-primary group-hover:text-ai">{next.title}</span>
                </button>
              ) : (
                <span />
              )}
            </div>
          </article>
        </main>

        {!presenting && <Toc section={section} activeHeading={activeHeading} onJump={jump} />}
      </div>
    </div>
  );
}
