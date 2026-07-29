import type { Metadata } from "next";
import { PresentationApp } from "@/components/presentation/presentation-app";

/**
 * Hidden Presentation Mode route → URL `/__present`.
 *
 * The folder on disk is `%5F%5Fpresent`: Next.js treats a literal leading
 * underscore as a private (non-routable) folder, and `%5F` is the URL-encoded
 * underscore that restores the intended segment.
 *
 * The route is excluded from indexing (noindex/nofollow), blocked in robots.ts,
 * and never linked from the app navigation.
 */
export const metadata: Metadata = {
  title: "Presentation Mode",
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: { index: false, follow: false },
  },
};

export default function PresentationRoute() {
  return <PresentationApp />;
}
