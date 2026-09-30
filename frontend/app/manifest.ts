import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FieldApp — إدارة العمليات الميدانية",
    short_name: "FieldApp",
    description: "إدارة المهام والتقارير والتواصل الميداني",
    start_url: "/",
    display: "standalone",
    background_color: "#f8fafc",
    theme_color: "#635bff",
    dir: "rtl",
    lang: "ar",
    icons: [{ src: "/logo.png", sizes: "192x192", type: "image/png", purpose: "maskable" }, { src: "/logo.png", sizes: "512x512", type: "image/png", purpose: "maskable" }],
  };
}
