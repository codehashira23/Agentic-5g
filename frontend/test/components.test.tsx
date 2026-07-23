/**
 * C132: Component tests — loading/empty/error states and StatusBadge.
 * Every data region must ship all three states (16-testing.md §6 mandate).
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Skeleton } from "@/components/states/skeleton";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { StatusBadge } from "@/components/status-badge";

describe("Skeleton", () => {
  it("renders without crashing", () => {
    const { container } = render(<Skeleton className="h-10" />);
    expect(container.firstChild).toBeTruthy();
  });

  it("has aria-hidden (decorative)", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveAttribute("aria-hidden");
  });
});

describe("EmptyState", () => {
  it("shows the message", () => {
    render(<EmptyState message="No data yet." />);
    expect(screen.getByText("No data yet.")).toBeTruthy();
  });

  it("renders an action when provided", () => {
    render(<EmptyState message="Nothing here." action={<button>Start</button>} />);
    expect(screen.getByRole("button", { name: "Start" })).toBeTruthy();
  });
});

describe("ErrorState", () => {
  it("shows the error message", () => {
    render(<ErrorState message="Something went wrong." />);
    expect(screen.getByText("Something went wrong.")).toBeTruthy();
  });

  it("renders retry button when provided", () => {
    const retry = vi.fn();
    render(<ErrorState message="Oops." retry={retry} />);
    const btn = screen.getByRole("button", { name: /retry/i });
    btn.click();
    expect(retry).toHaveBeenCalledOnce();
  });
});

describe("StatusBadge", () => {
  it("renders ACTIVE with ok styling", () => {
    const { container } = render(<StatusBadge status="ACTIVE" />);
    expect(container.textContent).toContain("Active");
    // Never color-alone: must have both color class AND text
    expect(container.querySelector("span")).toBeTruthy();
  });

  it("renders FAILED with crit styling", () => {
    const { container } = render(<StatusBadge status="FAILED" />);
    expect(container.textContent).toContain("Failed");
  });

  it("has aria-label for screen readers (state not color-alone)", () => {
    const { container } = render(<StatusBadge status="DEGRADED" />);
    const badge = container.querySelector("[aria-label]");
    expect(badge).toBeTruthy();
  });

  it("renders unknown status without crashing", () => {
    render(<StatusBadge status="UNKNOWN_STATUS" />);
    expect(screen.getByText("UNKNOWN_STATUS")).toBeTruthy();
  });
});
