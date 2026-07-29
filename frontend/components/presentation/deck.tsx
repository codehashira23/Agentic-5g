"use client";
import { useRef } from "react";
import { DeckProvider } from "@/lib/presentation/deck-context";
import { DeckStage } from "./deck-stage";

/** Owns the fullscreen target ref and provides deck state to the stage. */
export function Deck({ onExit }: { onExit: () => void }) {
  const rootRef = useRef<HTMLDivElement>(null);
  return (
    <DeckProvider rootRef={rootRef} onExit={onExit}>
      <DeckStage rootRef={rootRef} />
    </DeckProvider>
  );
}
