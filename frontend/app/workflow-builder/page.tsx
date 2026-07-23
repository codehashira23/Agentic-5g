"use client";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";
export default function WorkflowBuilderPage() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Workflow Builder</h1>
      <Panel title="Graph Canvas">
        <EmptyState message="Drag-and-drop workflow composition — Phase 8 stretch goal." />
      </Panel>
    </div>
  );
}
