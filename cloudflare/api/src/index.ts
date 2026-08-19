import { Container } from "@cloudflare/containers";
import { env } from "cloudflare:workers";

type Env = { FIELDAPP_API: DurableObjectNamespace; [key: string]: string | DurableObjectNamespace | undefined };
const secrets = env as unknown as Record<string, string | undefined>;
const secret = (name: string): string => secrets[name] ?? "";

/** A single API instance keeps websocket broadcasts coherent and runs migrations at boot. */
export class FieldAppApi extends Container {
  defaultPort = 8000;
  sleepAfter = "10m";
  envVars = {
    ENVIRONMENT: "production",
    DATABASE_URL: secret("DATABASE_URL"),
    REDIS_URL: secret("REDIS_URL"),
    JWT_SECRET: secret("JWT_SECRET"),
    FRONTEND_ORIGINS: secret("FRONTEND_ORIGINS"),
    INITIAL_ADMIN_USERNAME: secret("INITIAL_ADMIN_USERNAME"),
    INITIAL_ADMIN_PASSWORD: secret("INITIAL_ADMIN_PASSWORD"),
    INITIAL_ADMIN_NAME: secret("INITIAL_ADMIN_NAME"),
    DEFAULT_TECHNICIAN_PASSWORD: secret("DEFAULT_TECHNICIAN_PASSWORD"),
    SUPABASE_URL: secret("SUPABASE_URL"),
    SUPABASE_SERVICE_ROLE_KEY: secret("SUPABASE_SERVICE_ROLE_KEY"),
    SUPABASE_REPORTS_BUCKET: secret("SUPABASE_REPORTS_BUCKET"),
  };
}

export default {
  async fetch(request: Request, workerEnv: Env): Promise<Response> {
    const container = workerEnv.FIELDAPP_API.getByName("primary");
    try {
      return await container.fetch(request);
    } catch (error) {
      console.error("API container request failed", error);
      return Response.json({ detail: "الخدمة قيد التشغيل، أعد المحاولة بعد لحظات." }, { status: 503 });
    }
  },
};
