/**
 * C132: WS store reducer tests.
 * Verifies that apply() correctly updates state for each event type.
 * Owning docs: 11-frontend.md §9, 16-testing.md §6
 */
import { describe, it, expect, beforeEach } from "vitest";
import { useWsStore } from "@/lib/ws/store";
import type { WsEvent } from "@/lib/api/types.gen";

// Reset store between tests
beforeEach(() => {
  useWsStore.setState({
    connected: false,
    tick: 0,
    health_pct: 1.0,
    activeWorkflows: 0,
    nfStatusById: {},
    alerts: [],
    eventFeed: [],
  });
});

describe("WS store — setConnected", () => {
  it("sets connected true", () => {
    useWsStore.getState().setConnected(true);
    expect(useWsStore.getState().connected).toBe(true);
  });

  it("sets connected false", () => {
    useWsStore.getState().setConnected(true);
    useWsStore.getState().setConnected(false);
    expect(useWsStore.getState().connected).toBe(false);
  });
});

describe("WS store — apply NF_FAILED", () => {
  it("marks NF as FAILED in nfStatusById", () => {
    const evt: WsEvent = {
      type: "NF_FAILED",
      correlation_id: "wf_1",
      tick: 5,
      payload: { entity_id: "nrf_core_1", nf_type: "NRF", cause: "injected" },
    };
    useWsStore.getState().apply(evt);
    expect(useWsStore.getState().nfStatusById["nrf_core_1"]).toBe("FAILED");
  });

  it("adds alert on NF_FAILED", () => {
    const evt: WsEvent = {
      type: "NF_FAILED",
      tick: 5,
      payload: { entity_id: "upf_1", nf_type: "UPF", cause: "hazard" },
    };
    useWsStore.getState().apply(evt);
    const alerts = useWsStore.getState().alerts;
    expect(alerts.length).toBe(1);
    expect(alerts[0].type).toBe("NF_FAILED");
    expect(alerts[0].message).toContain("upf_1");
  });

  it("appends event to feed", () => {
    const evt: WsEvent = {
      type: "NF_FAILED",
      tick: 1,
      payload: { entity_id: "x", nf_type: "AMF", cause: "test" },
    };
    useWsStore.getState().apply(evt);
    expect(useWsStore.getState().eventFeed.length).toBe(1);
  });
});

describe("WS store — apply NF_RECOVERED", () => {
  it("marks NF as ACTIVE after recovery", () => {
    // First mark as failed
    useWsStore.getState().apply({
      type: "NF_FAILED",
      tick: 1,
      payload: { entity_id: "nrf_1", nf_type: "NRF", cause: "test" },
    });
    // Then recover
    useWsStore.getState().apply({
      type: "NF_RECOVERED",
      tick: 2,
      payload: { entity_id: "nrf_1", nf_type: "NRF" },
    });
    expect(useWsStore.getState().nfStatusById["nrf_1"]).toBe("ACTIVE");
  });
});

describe("WS store — apply KPI_THRESHOLD_BREACH", () => {
  it("adds breach alert with message", () => {
    const evt: WsEvent = {
      type: "KPI_THRESHOLD_BREACH",
      tick: 10,
      payload: {
        entity_id: "upf_mumbai_1",
        kpi: "latency_ms",
        value: 22.5,
        threshold: 20.0,
        region: "Mumbai",
      },
    };
    useWsStore.getState().apply(evt);
    const alerts = useWsStore.getState().alerts;
    expect(alerts.length).toBe(1);
    expect(alerts[0].type).toBe("KPI_THRESHOLD_BREACH");
    expect(alerts[0].region).toBe("Mumbai");
    expect(alerts[0].message).toContain("upf_mumbai_1");
  });
});

describe("WS store — event feed cap", () => {
  it("caps event feed at MAX_FEED (200)", () => {
    for (let i = 0; i < 210; i++) {
      useWsStore.getState().apply({
        type: "NF_RECOVERED",
        tick: i,
        payload: { entity_id: `nf_${i}`, nf_type: "AMF" },
      });
    }
    expect(useWsStore.getState().eventFeed.length).toBeLessThanOrEqual(200);
  });
});

describe("WS store — unknown event type", () => {
  it("still appends to event feed (fallback branch)", () => {
    useWsStore.getState().apply({
      type: "SOME_UNKNOWN_EVENT",
      tick: 0,
      payload: {},
    } as WsEvent);
    expect(useWsStore.getState().eventFeed.length).toBe(1);
  });
});
