"use client";
import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}
interface State {
  error: Error | null;
}

/**
 * Top-level error boundary — catches any error that escapes React Query's
 * error handling and shows a friendly recovery screen instead of the
 * Next.js white crash page.
 */
export class AppErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    const isNetworkError =
      error.message.includes("fetch") ||
      error.message.includes("404") ||
      error.message.includes("ECONNREFUSED");

    return (
      <div className="min-h-screen bg-base flex items-center justify-center p-8">
        <div className="bg-card border border-border rounded-xl p-8 max-w-lg w-full">
          <h1 className="text-crit text-lg font-bold mb-3">
            {isNetworkError ? "Backend not reachable" : "Something went wrong"}
          </h1>
          {isNetworkError ? (
            <>
              <p className="text-muted text-sm mb-4">
                The frontend cannot connect to the backend API at{" "}
                <code className="text-ai bg-card-hover px-1 rounded">localhost:8000</code>.
              </p>
              <p className="text-sm text-muted mb-4">To fix this:</p>
              <ol className="text-sm text-muted list-decimal pl-5 space-y-1">
                <li>
                  Open a PowerShell terminal and run:{" "}
                  <code className="text-ai bg-card-hover px-1 rounded">
                    .\scripts\run-backend.ps1
                  </code>
                </li>
                <li>Wait for "Uvicorn running on http://127.0.0.1:8000"</li>
                <li>
                  Refresh this page (<kbd className="bg-card-hover px-1 rounded text-xs">F5</kbd>)
                </li>
              </ol>
            </>
          ) : (
            <p className="text-muted text-sm mb-4">{error.message}</p>
          )}
          <button
            onClick={() => this.setState({ error: null })}
            className="mt-4 px-4 py-2 bg-ai/15 text-ai rounded-lg text-sm
                       hover:bg-ai/25 transition-colors"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }
}
