import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { NavRail } from "@/components/shell/nav-rail";
import { TopBar } from "@/components/shell/top-bar";
import { WsInit } from "@/lib/ws/ws-init";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agent5G — Agentic AI for 5G Advanced",
  description: "Autonomous operations platform for 5G Advanced Release 20",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-base text-primary">
        <Providers>
          <WsInit />
          <div className="flex flex-1 overflow-hidden">
            <NavRail />
            <div className="flex flex-col flex-1 overflow-hidden">
              <TopBar />
              <main className="flex-1 overflow-auto p-6">{children}</main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
