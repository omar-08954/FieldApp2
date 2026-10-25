"use client";

import { useEffect, useRef } from "react";

export function SignaturePad({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  useEffect(() => { if (!value) return; const context = canvas.current?.getContext("2d"); if (!context) return; const image = new Image(); image.onload = () => context.drawImage(image, 0, 0, 720, 180); image.src = value; }, [value]);
  const point = (event: React.PointerEvent<HTMLCanvasElement>) => { const rect = event.currentTarget.getBoundingClientRect(); return { x: (event.clientX - rect.left) * (720 / rect.width), y: (event.clientY - rect.top) * (180 / rect.height) }; };
  const start = (event: React.PointerEvent<HTMLCanvasElement>) => { const context = canvas.current?.getContext("2d"); if (!context) return; drawing.current = true; event.currentTarget.setPointerCapture(event.pointerId); const position = point(event); context.beginPath(); context.moveTo(position.x, position.y); };
  const move = (event: React.PointerEvent<HTMLCanvasElement>) => { if (!drawing.current) return; const context = canvas.current?.getContext("2d"); if (!context) return; const position = point(event); context.lineWidth = 2; context.lineCap = "round"; context.strokeStyle = "#1e293b"; context.lineTo(position.x, position.y); context.stroke(); onChange(canvas.current?.toDataURL("image/png") ?? ""); };
  const clear = () => { canvas.current?.getContext("2d")?.clearRect(0, 0, 720, 180); onChange(""); };
  return <div className="grid gap-2 sm:col-span-2"><div className="flex items-center justify-between text-sm text-slate-500"><span>توقيع العميل</span><button type="button" onClick={clear} className="text-xs text-brand">مسح التوقيع</button></div><canvas ref={canvas} width={720} height={180} onPointerDown={start} onPointerMove={move} onPointerUp={() => { drawing.current = false; }} onPointerCancel={() => { drawing.current = false; }} className="h-32 w-full touch-none rounded-xl border bg-white" aria-label="منطقة توقيع العميل" /></div>;
}
