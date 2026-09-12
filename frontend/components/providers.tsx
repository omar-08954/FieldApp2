"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";
import { RealtimeSync } from "./realtime-sync";
import { OfflineSync } from "./offline-sync";
export function Providers({ children }: { children: React.ReactNode }) { const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } })); return <ThemeProvider attribute="class" defaultTheme="system" enableSystem><QueryClientProvider client={client}><RealtimeSync client={client}/><OfflineSync/>{children}</QueryClientProvider></ThemeProvider>; }
