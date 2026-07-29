"use client";
import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import { Lock, KeyRound, ArrowRight } from "lucide-react";
import { ACCESS, PROJECT } from "@/lib/presentation/config";

/**
 * Secret unlock gate. Validates the passphrase and remembers a successful
 * unlock in localStorage so the presenter isn't prompted again on that device.
 */
export function PassphraseGate({ onUnlock }: { onUnlock: () => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (value.trim() === ACCESS.passphrase) {
      try {
        localStorage.setItem(ACCESS.unlockStorageKey, "1");
      } catch {
        /* storage may be unavailable — still allow this session */
      }
      onUnlock();
    } else {
      setError(true);
      setValue("");
    }
  };

  return (
    <div className="pv-root flex items-center justify-center px-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(700px circle at 50% 40%, color-mix(in srgb, var(--accent-ai) 10%, transparent), transparent 60%)",
        }}
      />
      <motion.form
        onSubmit={submit}
        initial={{ opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="glass relative z-10 w-[min(92vw,420px)] rounded-3xl border border-border bg-panel p-8 shadow-2"
      >
        <motion.div
          animate={error ? { x: [0, -9, 9, -6, 6, 0] } : {}}
          transition={{ duration: 0.4 }}
          className="flex flex-col items-center gap-5 text-center"
        >
          <span className="flex h-16 w-16 items-center justify-center rounded-2xl border border-ai/30 bg-ai/10 text-ai glow-ai">
            <Lock className="h-7 w-7" />
          </span>

          <div>
            <h1 className="font-display text-xl font-bold tracking-wide text-primary">
              Restricted area
            </h1>
            <p className="mt-1.5 text-sm text-muted">
              {PROJECT.fullName} Presentation Mode is private. Enter the passphrase to continue.
            </p>
          </div>

          <div className="w-full">
            <div
              className={`flex items-center gap-2 rounded-xl border bg-black/20 px-3 transition-colors ${
                error ? "border-crit/60" : "border-border focus-within:border-ai/50"
              }`}
            >
              <KeyRound className="h-4 w-4 shrink-0 text-faint" />
              <input
                autoFocus
                type="password"
                value={value}
                onChange={(e) => {
                  setValue(e.target.value);
                  setError(false);
                }}
                placeholder="Passphrase"
                aria-label="Passphrase"
                className="w-full bg-transparent py-3 text-sm text-primary placeholder:text-faint focus:outline-none"
              />
            </div>
            {error && <p className="mt-2 text-left text-xs text-crit">Incorrect passphrase. Try again.</p>}
          </div>

          <button
            type="submit"
            className="group inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-ai to-cyan py-3 text-sm font-semibold text-black transition-transform hover:scale-[1.02]"
          >
            Unlock presentation
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </button>
        </motion.div>
      </motion.form>
    </div>
  );
}
