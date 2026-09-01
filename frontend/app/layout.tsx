import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { AppSplash } from "@/components/app-splash";
export const metadata: Metadata = { title: "FieldApp", description: "Enterprise field operations" };
export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="ar" dir="rtl" suppressHydrationWarning><body><AppSplash><Providers>{children}</Providers></AppSplash></body></html>; }
