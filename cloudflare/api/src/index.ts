import { Container } from "@cloudflare/containers";
import { env } from "cloudflare:workers";

type Env = { FIELDAPP_API: DurableObjectNamespace; [key: string]: string | DurableObjectNamespace | undefined };

/** A single API instance keeps websocket broadcasts coherent and runs migrations at boot. */
export class FieldAppApi extends Container {
  defaultPort = 8000;
  sleepAfter = "10m";
  envVars = {
    ENVIRONMENT: "production",
    DATABASE_URL: env.DATABASE_URL,
    REDIS_URL: env.REDIS_URL,
    JWT_SECRET: env.JWT_SECRET,
    FRONTEND_ORIGINS: env.FRONTEND_ORIGINS,
    INITIAL_ADMIN_USERNAME: env.INITIAL_ADMIN_USERNAME,
    INITIAL_ADMIN_PASSWORD: env.INITIAL_ADMIN_PASSWORD,
    INITIAL_ADMIN_NAME: env.INITIAL_ADMIN_NAME,
    R2_ENDPOINT_URL: env.R2_ENDPOINT_URL,
    R2_ACCESS_KEY_ID: env.R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY: env.R2_SECRET_ACCESS_KEY,
    R2_BUCKET: env.R2_BUCKET,
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
