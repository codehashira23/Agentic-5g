"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Send, Wifi, WifiOff, Loader2 } from "lucide-react";
import { useWsStore } from "@/lib/ws/store";

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
    <header className="shrink-0 border-b border-border bg-panel/80 backdrop-blur-sm">
      <div className="flex items-center px-5 gap-3 h-14">
        {/* Intent input */}
        <form onSubmit={handleSubmit} className="flex-1 flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Ask Agent5G — e.g. Deploy congestion model to Delhi Edge"
              disabled={submitting}
              className="w-full bg-card border border-border rounded-xl px-4 py-2 text-sm
                         text-primary placeholder:text-faint
                         focus:outline-none focus:border-ai focus:ring-1 focus:ring-ai/20
                         disabled:opacity-50 transition-all pr-10"
            />
            {submitting && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ai animate-spin" />
            )}
          </div>
          <button
            type="submit"
            disabled={submitting || !goal.trim()}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium
                       bg-ai text-white hover:bg-ai/90 transition-all
                       disabled:opacity-40 disabled:cursor-not-allowed shadow-sm
                       active:scale-95"
            aria-label="Submit intent"
          >
            <Send className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Run</span>
          </button>
        </form>

        {/* WS status */}
        <div
          className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-colors ${
            connected
              ? "text-ok border-ok/20 bg-ok/5"
              : "text-warn border-warn/20 bg-warn/5"
          }`}
          title={connected ? "WebSocket connected" : "Disconnected — reconnecting…"}
        >
          {connected
            ? <Wifi className="w-3 h-3" />
            : <WifiOff className="w-3 h-3" />}
          <span className="font-medium">{connected ? "Live" : "Offline"}</span>
        </div>
      </div>

      {error && (
        <div className="px-5 pb-2">
          <p className="text-xs text-crit bg-crit/10 border border-crit/20 rounded-lg px-3 py-1.5">
            {error}
          </p>
        </div>
      )}
    </header>
  );
}
