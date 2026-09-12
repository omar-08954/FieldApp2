"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

export function AppSplash({ children }: { children: React.ReactNode }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    // Keep the brand animation without adding a noticeable delay before login.
    const timer = window.setTimeout(() => setVisible(false), 900);
    return () => window.clearTimeout(timer);
  }, []);

  return <>
    <div className={`fixed inset-0 z-[100] grid place-items-center bg-[#030605] transition-opacity duration-500 ${visible ? "opacity-100" : "pointer-events-none opacity-0"}`} aria-hidden={!visible}>
      <Image src="/fieldapp-animated-logo.gif" alt="FieldApp" width={500} height={500} priority className="h-auto w-[min(72vw,420px)] object-contain" unoptimized />
    </div>
    <div className={visible ? "invisible" : "visible"}>{children}</div>
  </>;
}
