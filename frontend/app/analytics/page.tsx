"use client";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";
export default function AnalyticsPage() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Analytics</h1>
      <Panel title="KPI Charts">
        <EmptyState message="Run experiments to generate analytics figures. Export via GET /analytics/export." />
      </Panel>
    </div>
  );
}
