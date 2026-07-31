import type { Metadata } from "next";
import { DocsApp } from "@/components/docs/docs-app";

/**
 * Hidden internal documentation / codebase walkthrough → URL `/internal`.
 *
 * Not linked anywhere in the app navigation, excluded from indexing
 * (noindex/nofollow) and blocked in robots.ts. Reachable only via the secret
 * URL. Renders a full-screen client docs app with presentation mode.
 */
export const metadata: Metadata = {
  title: "Internal Docs",
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: { index: false, follow: false },
  },
};

export default function InternalDocsRoute() {
  return <DocsApp />;
}
