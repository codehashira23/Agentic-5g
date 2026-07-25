import type { Metadata } from "next";
import { Space_Grotesk, Orbitron, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { NavRail } from "@/components/shell/nav-rail";
import { TopBar } from "@/components/shell/top-bar";
import { WsInit } from "@/lib/ws/ws-init";
import { AppErrorBoundary } from "@/components/error-boundary";
import { SplashScreen } from "@/components/splash-screen";

// Body + headings — modern technical sans
const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

// Logo / display — futuristic, fits 5G / telecom branding
const orbitron = Orbitron({
  variable: "--font-orbitron",
  subsets: ["latin"],
  weight: ["500", "700", "800", "900"],
});

// Monospace — code, ids, KPIs
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agent5G — Agentic AI for 5G Advanced",
  description: "Autonomous operations platform for 5G Advanced Release 20",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${orbitron.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-base text-primary">
        <SplashScreen />
        <Providers>
          <AppErrorBoundary>
            <WsInit />
            <div className="flex flex-1 overflow-hidden">
              <NavRail />
              <div className="flex flex-col flex-1 overflow-hidden">
                <TopBar />
                <main className="flex-1 overflow-auto p-6">{children}</main>
              </div>
            </div>
          </AppErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
