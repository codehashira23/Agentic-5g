"use client";
import { forwardRef, useMemo } from "react";
import { BookText, ListTree, Search, X } from "lucide-react";
import { GROUP_ORDER, SECTIONS, type DocSection } from "@/lib/docs/registry";
import { PROJECT_TREE, PROJECT_TREE_FILE_COUNT } from "@/lib/docs/project-tree";
import { FolderTree } from "./folder-tree";

type Tab = "contents" | "files";

function matches(section: DocSection, q: string) {
  if (!q) return true;
  const hay = `${section.title} ${section.group} ${section.toc.map((t) => t.label).join(" ")}`.toLowerCase();
  return hay.includes(q);
}

export const Sidebar = forwardRef<
  HTMLInputElement,
  {
    activeId: string;
    query: string;
    setQuery: (v: string) => void;
    tab: Tab;
    setTab: (t: Tab) => void;
    onSelect: (id: string) => void;
  }
>(function Sidebar({ activeId, query, setQuery, tab, setTab, onSelect }, searchRef) {
  const q = query.trim().toLowerCase();

  const filtered = useMemo(() => SECTIONS.filter((s) => matches(s, q)), [q]);
  const grouped = useMemo(
    () => GROUP_ORDER.map((g) => ({ group: g, items: filtered.filter((s) => s.group === g) })).filter((x) => x.items.length),
    [filtered],
  );

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-border bg-panel/60 backdrop-blur-xl">
      {/* Search */}
      <div className="p-3">
        <div className="flex items-center gap-2 rounded-lg border border-border bg-black/20 px-2.5 focus-within:border-ai/50">
          <Search className="h-4 w-4 shrink-0 text-faint" />
          <input
            ref={searchRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search docs & files…"
            aria-label="Search"
            className="w-full bg-transparent py-2 text-sm text-primary placeholder:text-faint focus:outline-none"
          />
          {query && (
            <button type="button" onClick={() => setQuery("")} aria-label="Clear search" className="text-faint hover:text-primary">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
          {!query && (
            <kbd className="rounded border border-border bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] text-faint">/</kbd>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-3 pb-2">
        {(
          [
            { id: "contents", label: "Contents", icon: BookText },
            { id: "files", label: "Files", icon: ListTree },
          ] as const
        ).map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === t.id ? "bg-ai/15 text-ai" : "text-muted hover:bg-card-hover hover:text-primary"
            }`}
          >
            <t.icon className="h-3.5 w-3.5" />
            {t.label}
            {t.id === "files" && <span className="text-[10px] text-faint">{PROJECT_TREE_FILE_COUNT}</span>}
          </button>
        ))}
      </div>

      {/* Body */}
      <nav className="pv-slide-scroll flex-1 overflow-y-auto px-2 pb-6">
        {tab === "contents" ? (
          grouped.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs text-faint">No sections match “{query}”.</p>
          ) : (
            grouped.map(({ group, items }) => (
              <div key={group} className="mb-3">
                <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-faint">{group}</p>
                {items.map((s) => {
                  const active = s.id === activeId;
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => onSelect(s.id)}
                      className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                        active ? "bg-ai/15 font-medium text-ai" : "text-muted hover:bg-card-hover hover:text-primary"
                      }`}
                    >
                      <s.icon className={`h-4 w-4 shrink-0 ${active ? "text-ai" : "text-faint"}`} />
                      <span className="flex-1 truncate">{s.title}</span>
                      {active && <span className="h-1.5 w-1.5 rounded-full bg-ai" />}
                    </button>
                  );
                })}
              </div>
            ))
          )
        ) : (
          <FolderTree nodes={PROJECT_TREE} query={query} activeSection={activeId} onOpen={onSelect} />
        )}
      </nav>
    </aside>
  );
});
