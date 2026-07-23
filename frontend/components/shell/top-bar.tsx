"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Send, Wifi, WifiOff } from "lucide-react";
import { useWsStore } from "@/lib/ws/store";

// Safe fallback so the URL is never "undefined/workflows" even before
// .env.local is created.  NEXT_PUBLIC_* vars are inlined at build time;
// the default here is the standard local dev address.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export function TopBar() {
  const [goal, setGoal] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const connected = useWsStore((s) => s.connected);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim() || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/workflows`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: goal.trim() }),
      });
      if (res.ok) {
        const wf = await res.json();
        setGoal("");
        router.push(`/agent-console?wf=${wf.id}`);
      } else {
        const body = await res.json().catch(() => ({}));
        setError(body.detail ?? `Server error ${res.status}`);
      }
    } catch {
      setError("Backend not reachable — is the server running?");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <header className="h-auto border-b border-border bg-panel shrink-0">
      <div className="flex items-center px-4 gap-4 h-14">
        <form onSubmit={handleSubmit} className="flex-1 flex items-center gap-2">
          <input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Ask Agent5G — e.g. Deploy congestion model to Delhi Edge"
            disabled={submitting}
            className="flex-1 bg-card border border-border rounded-lg px-3 py-1.5 text-sm
                       text-primary placeholder:text-faint focus:outline-none focus:border-ai
                       disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={submitting || !goal.trim()}
            className="p-2 rounded-lg bg-ai/15 text-ai hover:bg-ai/25 transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Submit intent"
          >
            <Send className={`w-4 h-4 ${submitting ? "animate-pulse" : ""}`} />
          </button>
        </form>
        <div
          className={`flex items-center gap-1 text-xs ${connected ? "text-ok" : "text-warn"}`}
          title={connected ? "Live — WebSocket connected" : "Disconnected — reconnecting…"}
        >
          {connected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          <span>{connected ? "Live" : "Offline"}</span>
        </div>
      </div>
      {error && <p className="px-4 pb-2 text-xs text-crit">{error}</p>}
    </header>
  );
}
