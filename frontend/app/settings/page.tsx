"use client";
import { useQuery } from "@tanstack/react-query";
import {
  Settings as SettingsIcon, Cpu, Database, Activity, Radio,
  Server, Globe, Gauge, Boxes,
  Info, Wifi, WifiOff, Code2, ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { useWsStore } from "@/lib/ws/store";

// ── Types ─────────────────────────────────────────────────────────────────────
type SettingsData = {
  llm: { mode: string; model: string; key_set: boolean };
  simulation: { default_seed: number; tick_ms: number; default_scenario: string };
  env: string;
};
type HealthData = { status: string; db: string; bus: string; llm: string; sim: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

// ── Status pill ───────────────────────────────────────────────────────────────
function StatusPill({
  label,
  ok,
  value,
  icon,
}: {
  label: string;
  ok: boolean;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className={`flex items-center gap-2.5 rounded-xl border px-3 py-2.5 backdrop-blur-xl
      ${ok ? "border-ok/25 bg-ok/5" : "border-crit/25 bg-crit/5"}`}>
      <span className={ok ? "text-ok" : "text-crit"}>{icon}</span>
      <div className="min-w-0">
        <p className="text-[10px] text-faint uppercase tracking-wider leading-none">{label}</p>
        <p className={`text-xs font-semibold mt-1 leading-none ${ok ? "text-ok" : "text-crit"}`}>
          {value}
        </p>
      </div>
    </div>
  );
}

// ── Config row ────────────────────────────────────────────────────────────────
function ConfigRow({
  label,
  value,
  mono = false,
  badge,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  badge?: { text: string; cls: string };
}) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border/50 last:border-0">
      <span className="text-xs text-muted">{label}</span>
      {badge ? (
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${badge.cls}`}>
          {badge.text}
        </span>
      ) : (
        <span className={`text-xs text-primary ${mono ? "font-mono" : "font-medium"}`}>
          {value}
        </span>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function SettingsPage() {
  const connected = useWsStore((s) => s.connected);

  const { data: settings } = useQuery<SettingsData>({
    queryKey: keys.settings(),
    queryFn: () => api.get<SettingsData>("/settings"),
  });

  const { data: health } = useQuery<HealthData>({
    queryKey: ["health"],
    queryFn: () => api.get<HealthData>("/health"),
    refetchInterval: 5000,
  });

  const backendOk = !!health || !!settings;
  const isLive = settings?.llm.mode === "live";

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-ai/20 to-cyan/10 border border-ai/25 flex items-center justify-center text-ai shrink-0">
          <SettingsIcon className="w-4 h-4" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-primary">Settings</h1>
          <p className="text-xs text-faint mt-0.5">Platform configuration and live system status</p>
        </div>
      </div>

      {/* System status pills */}
      <div>
        <p className="section-eyebrow brand-gradient mb-2">System Status</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          <StatusPill label="Backend" ok={backendOk}
            value={backendOk ? "Online" : "Offline"} icon={<Server className="w-4 h-4" />} />
          <StatusPill label="Database" ok={health?.db === "ok"}
            value={health?.db === "ok" ? "Connected" : "—"} icon={<Database className="w-4 h-4" />} />
          <StatusPill label="Event Bus" ok={health?.bus === "ok"}
            value={health?.bus === "ok" ? "Active" : "—"} icon={<Activity className="w-4 h-4" />} />
          <StatusPill label="LLM" ok={health?.llm === "ready"}
            value={health?.llm === "ready" ? "Ready" : "—"} icon={<Cpu className="w-4 h-4" />} />
          <StatusPill label="Simulation" ok={health?.sim === "running"}
            value={health?.sim ?? "—"} icon={<Radio className="w-4 h-4" />} />
          <StatusPill label="WebSocket" ok={connected}
            value={connected ? "Live" : "Offline"}
            icon={connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />} />
        </div>
      </div>

      {/* Two-column config */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* LLM */}
        <Panel
          title="LLM Configuration"
          actions={<Cpu className="w-4 h-4 text-ai" />}
        >
          <ConfigRow
            label="Mode"
            value=""
            badge={{
              text: settings?.llm.mode ?? "—",
              cls: isLive ? "text-ai bg-ai/10 border-ai/25" : "text-faint bg-card border-border",
            }}
          />
          <ConfigRow label="Provider" value={isLive ? "Groq" : "Replay fixtures"} />
          <ConfigRow label="Model" value={settings?.llm.model ?? "—"} mono />
          <ConfigRow
            label="API Key"
            value=""
            badge={
              settings?.llm.key_set
                ? { text: "Configured", cls: "text-ok bg-ok/10 border-ok/25" }
                : { text: "Not set", cls: "text-crit bg-crit/10 border-crit/25" }
            }
          />
        </Panel>

        {/* Simulation */}
        <Panel
          title="Simulation Configuration"
          actions={<Gauge className="w-4 h-4 text-ai" />}
        >
          <ConfigRow label="Default Seed" value={settings?.simulation.default_seed ?? "—"} mono />
          <ConfigRow label="Tick Interval" value={`${settings?.simulation.tick_ms ?? "—"} ms`} mono />
          <ConfigRow label="Default Scenario" value={settings?.simulation.default_scenario ?? "—"} mono />
          <ConfigRow
            label="Environment"
            value=""
            badge={{
              text: settings?.env ?? "—",
              cls: "text-info bg-info/10 border-info/25",
            }}
          />
        </Panel>

        {/* Connection */}
        <Panel title="Connection" actions={<Globe className="w-4 h-4 text-ai" />}>
          <ConfigRow label="API Base URL" value={API_BASE} mono />
          <ConfigRow label="WebSocket URL" value={WS_URL} mono />
          <ConfigRow
            label="Live Connection"
            value=""
            badge={
              connected
                ? { text: "Connected", cls: "text-ok bg-ok/10 border-ok/25" }
                : { text: "Reconnecting", cls: "text-warn bg-warn/10 border-warn/25" }
            }
          />
        </Panel>

        {/* About */}
        <Panel title="About Agent5G" actions={<Info className="w-4 h-4 text-ai" />}>
          <p className="text-xs text-muted leading-relaxed mb-3">
            Agentic AI Service Enablement Platform for 5G Advanced Release 20.
            Autonomous AI agents observe, reason, plan, and act on a simulated
            5G Core Digital Twin.
          </p>
          <p className="text-[10px] text-faint uppercase tracking-wider mb-1.5">Tech Stack</p>
          <div className="flex flex-wrap gap-1.5 mb-4">
            {["Next.js", "FastAPI", "Groq LLM", "SQLite", "React Flow", "WebSocket"].map((t) => (
              <span key={t} className="px-2 py-0.5 rounded-md bg-card border border-border text-[10px] text-muted">
                {t}
              </span>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <a
              href="https://github.com/codehashira23/Agentic-5g"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card border border-border
                         text-xs text-muted hover:text-primary hover:border-ai/40 transition-colors"
            >
              <Code2 className="w-3.5 h-3.5" /> GitHub
            </a>
            <a
              href={API_BASE.replace("/api/v1", "/docs")}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card border border-border
                         text-xs text-muted hover:text-primary hover:border-ai/40 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" /> API Docs
            </a>
          </div>
        </Panel>
      </div>

      {/* Config note */}
      <div className="flex items-start gap-2 rounded-xl border border-border bg-card/50 backdrop-blur-xl px-4 py-3">
        <Boxes className="w-4 h-4 text-ai shrink-0 mt-0.5" />
        <p className="text-xs text-muted leading-relaxed">
          Configuration is loaded from environment variables (<span className="font-mono text-faint">.env</span>).
          To change the LLM provider, simulation seed, or scenario, update the backend
          environment and restart the server. Secrets like the API key are never exposed by the API.
        </p>
      </div>
    </div>
  );
}
