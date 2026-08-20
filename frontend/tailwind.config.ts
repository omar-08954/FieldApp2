import type { Config } from "tailwindcss";
export default { darkMode: "class", content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"], theme: { extend: { fontFamily: { sans: ["Tahoma", "Arial", "sans-serif"] }, colors: { ink: "#101828", canvas: "#f8fafc", brand: "#635bff" }, boxShadow: { soft: "0 18px 40px rgba(15, 23, 42, .08)" } } }, plugins: [] } satisfies Config;
