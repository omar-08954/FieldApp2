"use client";

import { Printer } from "lucide-react";

export function PrintReportButton() {
  return <button type="button" onClick={() => window.print()} className="print-hidden fixed bottom-5 left-5 z-30 inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white shadow-lg"><Printer size={17} />طباعة / حفظ PDF</button>;
}
