import { create } from "zustand";
import type { WsEvent } from "@/lib/api/types.gen";
import { queryClient } from "@/lib/query/client";

const MAX_FEED = 200;

export interface Alert {
  id: string;
  type: string;
  message: string;
  region?: string;
  ts: string;
}

export interface WsState {
  connected: boolean;
  tick: number;
  health_pct: number;
  activeWorkflows: number;
  nfStatusById: Record<string, string>;
  alerts: Alert[];
  eventFeed: WsEvent[];
  setConnected: (v: boolean) => void;
  apply: (e: WsEvent) => void;
}

export const useWsStore = create<WsState>((set) => ({
  connected: false,
  tick: 0,
  health_pct: 1.0,
  activeWorkflows: 0,
  nfStatusById: {},
  alerts: [],
  eventFeed: [],

  setConnected: (v) => set({ connected: v }),

  apply: (e) =>
    set((state) => {
      const feed = [e, ...state.eventFeed].slice(0, MAX_FEED);
      switch (e.type) {
        case "NF_FAILED": {
          const p = e.payload as { entity_id: string; cause: string };
          // Instantly refresh topology + twin pages
          queryClient.invalidateQueries({ queryKey: ["twin"] });
          queryClient.invalidateQueries({ queryKey: ["topology"] });
          return {
            eventFeed: feed,
            nfStatusById: { ...state.nfStatusById, [p.entity_id]: "FAILED" },
            alerts: [
              {
                id: e.correlation_id ?? Date.now().toString(),
                type: "NF_FAILED",
                message: `${p.entity_id} FAILED (${p.cause})`,
                ts:
                  typeof e === "object" && "ts" in e ? String((e as { ts?: string }).ts ?? "") : "",
              },
              ...state.alerts,
            ].slice(0, 50),
          };
        }
        case "NF_RECOVERED": {
          const p = e.payload as { entity_id: string };
          queryClient.invalidateQueries({ queryKey: ["twin"] });
          queryClient.invalidateQueries({ queryKey: ["topology"] });
          return {
            eventFeed: feed,
            nfStatusById: { ...state.nfStatusById, [p.entity_id]: "ACTIVE" },
          };
        }
        case "KPI_THRESHOLD_BREACH": {
          const p = e.payload as { entity_id: string; kpi: string; value: number; region: string };
          return {
            eventFeed: feed,
            alerts: [
              {
                id: e.correlation_id ?? Date.now().toString(),
                type: "KPI_THRESHOLD_BREACH",
                message: `${p.kpi} breach on ${p.entity_id} (${p.value.toFixed(1)})`,
                region: String(p.region ?? ""),
                ts:
                  typeof e === "object" && "ts" in e ? String((e as { ts?: string }).ts ?? "") : "",
              },
              ...state.alerts,
            ].slice(0, 50),
          };
        }
        case "WORKFLOW_STAGE_CHANGED": {
          // Instantly refresh the workflows list so the stepper updates
          queryClient.invalidateQueries({ queryKey: ["workflows"] });
          return { eventFeed: feed, activeWorkflows: state.activeWorkflows };
        }
        case "WORKFLOW_COMPLETED":
        case "WORKFLOW_FAILED": {
          queryClient.invalidateQueries({ queryKey: ["workflows"] });
          return { eventFeed: feed };
        }
        default:
          return { eventFeed: feed };
      }
    }),
}));
