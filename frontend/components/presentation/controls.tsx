"use client";
import {
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  HelpCircle,
  LayoutGrid,
  Maximize,
  Minimize,
  Moon,
  MousePointer2,
  PauseCircle,
  PlayCircle,
  Sun,
  Timer,
  Volume2,
  VolumeX,
  X,
  type LucideIcon,
} from "lucide-react";
import { formatElapsed, useDeck } from "@/lib/presentation/deck-context";

function CtrlButton({
  icon: IconCmp,
  label,
  onClick,
  active = false,
  disabled = false,
}: {
  icon: LucideIcon;
  label: string;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      aria-pressed={active}
      className={`inline-flex h-9 w-9 items-center justify-center rounded-lg border transition-all disabled:cursor-not-allowed disabled:opacity-30 ${
        active
          ? "border-ai/50 bg-ai/15 text-ai"
          : "border-transparent text-muted hover:border-border hover:bg-card-hover hover:text-primary"
      }`}
    >
      <IconCmp className="h-[18px] w-[18px]" />
    </button>
  );
}

export function Controls({ visible }: { visible: boolean }) {
  const d = useDeck();

  return (
    <>
      {/* Always-visible progress bar pinned to the bottom edge */}
      <div className="absolute inset-x-0 bottom-0 z-[10020] h-1 bg-white/[0.06]">
        <div
          className="h-full bg-gradient-to-r from-ai to-cyan transition-[width] duration-500 ease-out"
          style={{ width: `${d.progress * 100}%` }}
        />
      </div>

      {/* Auto-hiding control bar */}
      <div
        className={`absolute inset-x-0 bottom-0 z-[10021] flex items-center justify-between gap-3 px-4 pb-4 pt-8 transition-all duration-300 md:px-6 ${
          visible ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-4 opacity-0"
        }`}
      >
        {/* Left — counter + timer */}
        <div className="flex items-center gap-2">
          <span className="glass rounded-lg border border-border px-3 py-1.5 font-mono text-sm text-primary">
            <span className="text-ai">{String(d.index + 1).padStart(2, "0")}</span>
            <span className="text-faint"> / {String(d.total).padStart(2, "0")}</span>
          </span>
          <button
            type="button"
            onClick={d.resetTimer}
            title="Elapsed time (click to reset)"
            className="glass hidden items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 font-mono text-sm text-muted transition-colors hover:text-primary sm:inline-flex"
          >
            <Timer className="h-4 w-4 text-ai" />
            {formatElapsed(d.elapsedMs)}
          </button>
        </div>

        {/* Center — prev / next */}
        <div className="glass flex items-center gap-1 rounded-xl border border-border p-1">
          <CtrlButton icon={ChevronLeft} label="Previous" onClick={d.prev} disabled={d.atStart} />
          <CtrlButton icon={ChevronRight} label="Next" onClick={d.next} disabled={d.atEnd} />
        </div>

        {/* Right — toolbar */}
        <div className="glass flex items-center gap-0.5 rounded-xl border border-border p-1">
          <CtrlButton
            icon={d.autoplay ? PauseCircle : PlayCircle}
            label={d.autoplay ? "Pause autoplay" : "Autoplay"}
            onClick={d.toggleAutoplay}
            active={d.autoplay}
          />
          <CtrlButton icon={LayoutGrid} label="Overview" onClick={d.toggleOverview} active={d.overview} />
          <CtrlButton icon={ClipboardList} label="Presenter notes" onClick={d.toggleNotes} active={d.notes} />
          <CtrlButton icon={MousePointer2} label="Laser pointer" onClick={d.toggleLaser} active={d.laser} />
          <CtrlButton
            icon={d.music ? Volume2 : VolumeX}
            label={d.music ? "Mute music" : "Play music"}
            onClick={d.toggleMusic}
            active={d.music}
          />
          <CtrlButton
            icon={d.theme === "dark" ? Sun : Moon}
            label="Toggle theme"
            onClick={d.toggleTheme}
          />
          <CtrlButton
            icon={d.isFullscreen ? Minimize : Maximize}
            label="Toggle fullscreen"
            onClick={d.toggleFullscreen}
            active={d.isFullscreen}
          />
          <CtrlButton icon={HelpCircle} label="Keyboard shortcuts (H)" onClick={d.toggleHelp} active={d.help} />
          <span className="mx-1 h-5 w-px bg-border" />
          <CtrlButton icon={X} label="Exit presentation" onClick={d.exitPresentation} />
        </div>
      </div>
    </>
  );
}
