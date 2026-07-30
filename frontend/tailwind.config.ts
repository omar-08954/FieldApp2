import type { Config } from "tailwindcss";
export default { content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"], theme: { extend: { fontFamily: { sans: ["var(--font-ibm-plex-arabic)", "sans-serif"] }, colors: { ink: "#101828", canvas: "#f8fafc", brand: "#635bff" }, boxShadow: { soft: "0 18px 40px rgba(15, 23, 42, .08)" } } }, plugins: [] } satisfies Config;
