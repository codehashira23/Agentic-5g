"use client";
import { Clock } from "lucide-react";
import type { DocSection } from "@/lib/docs/registry";

export function Toc({
  section,
  activeHeading,
  onJump,
}: {
  section: DocSection;
  activeHeading: string | null;
  onJump: (id: string) => void;
}) {
  return (
    <aside className="hidden w-60 shrink-0 overflow-y-auto border-l border-border px-5 py-8 xl:block">
      <p className="section-eyebrow mb-3 text-faint">On this page</p>
      <ul className="flex flex-col gap-1.5 border-l border-border">
        {section.toc.map((t) => {
          const active = t.id === activeHeading;
          return (
            <li key={t.id}>
              <button
                type="button"
                onClick={() => onJump(t.id)}
                className={`-ml-px border-l-2 pl-3 text-left text-[13px] leading-5 transition-colors ${
                  active
                    ? "border-ai font-medium text-ai"
                    : "border-transparent text-faint hover:border-border hover:text-muted"
                }`}
              >
                {t.label}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="mt-6 flex items-center gap-1.5 border-t border-border pt-4 text-xs text-faint">
        <Clock className="h-3.5 w-3.5" />
        {section.minutes} min read
      </div>
    </aside>
  );
}
