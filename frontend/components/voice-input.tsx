"use client";

import { Mic, MicOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type Recognition = { lang: string; interimResults: boolean; continuous: boolean; start: () => void; stop: () => void; onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null; onend: (() => void) | null; onerror: (() => void) | null };
type RecognitionWindow = Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };

export function VoiceInput({ onText }: { onText: (text: string) => void }) {
  const recognition = useRef<Recognition | undefined>(undefined);
  const [listening, setListening] = useState(false);
  useEffect(() => () => recognition.current?.stop(), []);
  function toggle() {
    if (listening) { recognition.current?.stop(); setListening(false); return; }
    const Constructor = (window as RecognitionWindow).SpeechRecognition ?? (window as RecognitionWindow).webkitSpeechRecognition;
    if (!Constructor) return;
    const instance = new Constructor(); instance.lang = "ar-SA"; instance.interimResults = false; instance.continuous = false;
    instance.onresult = event => onText(Array.from(event.results).map(result => result[0].transcript).join(" "));
    instance.onend = () => setListening(false); instance.onerror = () => setListening(false); recognition.current = instance; instance.start(); setListening(true);
  }
  return <button type="button" onClick={toggle} className={`rounded-xl border p-3 ${listening ? "border-red-400 bg-red-50 text-red-600" : "hover:bg-slate-50 dark:hover:bg-slate-800"}`} aria-label={listening ? "إيقاف التسجيل" : "إدخال صوتي"} title="إملاء صوتي بالعربية">{listening ? <MicOff size={18}/> : <Mic size={18}/>}</button>;
}
