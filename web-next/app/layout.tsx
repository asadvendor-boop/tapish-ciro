import type { Metadata } from "next";
import { Inter, Noto_Naskh_Arabic } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });
const notoNaskh = Noto_Naskh_Arabic({ subsets: ["arabic"], weight: ["400", "500", "600", "700"], variable: "--font-urdu" });

export const metadata: Metadata = {
  title: "تپش مرکز — Tapish Markaz | CIRO Command Centre",
  description: "Real-time agentic crisis response dashboard for Lahore. 6-agent ADK pipeline with live map, trace console, and signal injection.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} ${notoNaskh.variable}`}>{children}</body>
    </html>
  );
}
