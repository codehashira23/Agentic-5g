"use client";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";
export default function MemoryPage() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Memory Viewer</h1>
      <Panel title="Episodic">
        <EmptyState message="Episodic memories accumulate after workflows complete." />
      </Panel>
    </div>
  );
}
