import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Agent5G — Agentic AI for 5G Advanced",
  description:
    "Agentic AI Service Enablement Platform for 5G Advanced Release 20. " +
    "Observe, reason, plan, execute, and recover — autonomously.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    /*
     * Dark-first: no class = dark theme (tokens default to dark).
     * Add class="light" here (or via a theme provider in a later commit)
     * to switch to the light palette.
     */
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-base text-primary">{children}</body>
    </html>
  );
}
