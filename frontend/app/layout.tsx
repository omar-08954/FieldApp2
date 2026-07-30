import type { Metadata } from "next";
import { IBM_Plex_Sans_Arabic } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
const font = IBM_Plex_Sans_Arabic({ subsets: ["arabic", "latin"], variable: "--font-ibm-plex-arabic", weight: ["400", "500", "600", "700"] });
export const metadata: Metadata = { title: "FieldApp", description: "Enterprise field operations" };
export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="ar" dir="rtl" suppressHydrationWarning><body className={font.variable}><Providers>{children}</Providers></body></html>; }
