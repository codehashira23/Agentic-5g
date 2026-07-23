"use client";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";
export default function KnowledgeGraphPage() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Knowledge Graph</h1>
      <Panel title="Entities and Relations">
        <EmptyState message="Knowledge graph grows as agents learn from workflows." />
      </Panel>
    </div>
  );
}
