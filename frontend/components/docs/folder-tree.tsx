"use client";
import { useMemo, useState } from "react";
import { ChevronRight, FileCode2, FileCog, FileJson, FileText, Folder, FolderOpen } from "lucide-react";
import type { TreeNode } from "@/lib/docs/project-tree";
import { sectionForPath } from "@/lib/docs/registry";

function FileGlyph({ name }: { name: string }) {
  const ext = name.slice(name.lastIndexOf(".") + 1).toLowerCase();
  const cls = "h-3.5 w-3.5 shrink-0";
  if (["py", "ts", "tsx", "js", "mjs", "jsx"].includes(ext)) return <FileCode2 className={`${cls} text-cyan/70`} />;
  if (ext === "json") return <FileJson className={`${cls} text-faint`} />;
  if (["toml", "env", "example", "config", "mjs"].includes(ext) || name.startsWith(".env"))
    return <FileCog className={`${cls} text-faint`} />;
  return <FileText className={`${cls} text-faint`} />;
}

function filterTree(nodes: TreeNode[], q: string): TreeNode[] {
  const out: TreeNode[] = [];
  for (const n of nodes) {
    if (n.type === "file") {
      if (n.name.toLowerCase().includes(q) || n.path.toLowerCase().includes(q)) out.push(n);
    } else {
      const kids = filterTree(n.children ?? [], q);
      if (kids.length || n.name.toLowerCase().includes(q)) {
        out.push({ ...n, children: kids.length ? kids : (n.children ?? []) });
      }
    }
  }
  return out;
}

interface ItemProps {
  node: TreeNode;
  depth: number;
  searching: boolean;
  expanded: Set<string>;
  toggle: (p: string) => void;
  activeSection: string;
  onOpen: (sectionId: string) => void;
}

function TreeItem({ node, depth, searching, expanded, toggle, activeSection, onOpen }: ItemProps) {
  const pad = { paddingLeft: `${depth * 12 + 8}px` };

  if (node.type === "dir") {
    const isOpen = searching || expanded.has(node.path);
    return (
      <li>
        <button
          type="button"
          onClick={() => toggle(node.path)}
          style={pad}
          className="flex w-full items-center gap-1.5 rounded-md py-1 pr-2 text-left text-[13px] text-muted transition-colors hover:bg-card-hover hover:text-primary"
        >
          <ChevronRight className={`h-3.5 w-3.5 shrink-0 text-faint transition-transform ${isOpen ? "rotate-90" : ""}`} />
          {isOpen ? <FolderOpen className="h-3.5 w-3.5 shrink-0 text-ai/80" /> : <Folder className="h-3.5 w-3.5 shrink-0 text-ai/60" />}
          <span className="truncate">{node.name}</span>
        </button>
        {isOpen && node.children && (
          <ul>
            {node.children.map((c) => (
              <TreeItem
                key={c.path}
                node={c}
                depth={depth + 1}
                searching={searching}
                expanded={expanded}
                toggle={toggle}
                activeSection={activeSection}
                onOpen={onOpen}
              />
            ))}
          </ul>
        )}
      </li>
    );
  }

  const sectionId = sectionForPath(node.path);
  const documented = Boolean(sectionId);
  return (
    <li>
      <button
        type="button"
        disabled={!documented}
        onClick={() => sectionId && onOpen(sectionId)}
        style={pad}
        title={documented ? "Open documentation" : "No dedicated docs section"}
        className={`group flex w-full items-center gap-1.5 rounded-md py-1 pr-2 text-left text-[13px] transition-colors ${
          documented
            ? "cursor-pointer text-muted hover:bg-card-hover hover:text-primary"
            : "cursor-default text-faint/70"
        } ${sectionId && sectionId === activeSection ? "text-ai" : ""}`}
      >
        <span className="w-3.5 shrink-0" />
        <FileGlyph name={node.name} />
        <span className="truncate">{node.name}</span>
        {documented && (
          <span className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-ai/50 opacity-0 transition-opacity group-hover:opacity-100" />
        )}
      </button>
    </li>
  );
}

export function FolderTree({
  nodes,
  query,
  activeSection,
  onOpen,
}: {
  nodes: TreeNode[];
  query: string;
  activeSection: string;
  onOpen: (sectionId: string) => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(
    () =>
      new Set([
        "backend",
        "frontend",
        "backend/app",
        "frontend/app",
        "frontend/lib",
        "backend/app/api",
        "backend/app/application",
        "backend/app/infrastructure",
      ]),
  );
  const q = query.trim().toLowerCase();
  const searching = q.length > 0;
  const shown = useMemo(() => (searching ? filterTree(nodes, q) : nodes), [nodes, q, searching]);
  const toggle = (p: string) =>
    setExpanded((s) => {
      const n = new Set(s);
      if (n.has(p)) n.delete(p);
      else n.add(p);
      return n;
    });

  if (searching && shown.length === 0) {
    return <p className="px-2 py-4 text-center text-xs text-faint">No files match “{query}”.</p>;
  }

  return (
    <ul className="pb-4">
      {shown.map((n) => (
        <TreeItem
          key={n.path}
          node={n}
          depth={0}
          searching={searching}
          expanded={expanded}
          toggle={toggle}
          activeSection={activeSection}
          onOpen={onOpen}
        />
      ))}
    </ul>
  );
}
