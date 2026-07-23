"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Send, Wifi, WifiOff } from "lucide-react";
import { useWsStore } from "@/lib/ws/store";

export function TopBar() {
  const [goal, setGoal] = useState("");
  const router = useRouter();
  const connected = useWsStore((s) => s.connected);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim()) return;
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/workflows`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: goal.trim() }),
      });
      if (res.ok) {
        const wf = await res.json();
        setGoal("");
        router.push(`/agent-console?wf=${wf.id}`);
      }
    } catch {
      /* backend not running in dev — silently ignore */
    }
  }

  return (
    <header className="h-14 border-b border-border bg-panel flex items-center px-4 gap-4 shrink-0">
      <form onSubmit={handleSubmit} className="flex-1 flex items-center gap-2">
        <input
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Ask Agent5G — e.g. Deploy congestion model to Delhi Edge"
          className="flex-1 bg-card border border-border rounded-lg px-3 py-1.5 text-sm
                     text-primary placeholder:text-faint focus:outline-none focus:border-ai"
        />
        <button
          type="submit"
          className="p-2 rounded-lg bg-ai/15 text-ai hover:bg-ai/25 transition-colors"
          aria-label="Submit intent"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
      <div
        className={`flex items-center gap-1 text-xs ${connected ? "text-ok" : "text-warn"}`}
        title={connected ? "Live — WebSocket connected" : "Disconnected — reconnecting…"}
      >
        {connected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
        <span>{connected ? "Live" : "Offline"}</span>
      </div>
    </header>
  );
}
