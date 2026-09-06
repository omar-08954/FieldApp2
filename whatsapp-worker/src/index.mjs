import makeWASocket, { DisconnectReason, useMultiFileAuthState } from "@whiskeysockets/baileys";
import { createServer } from "node:http";
import cron from "node-cron";
import pino from "pino";
import qrcode from "qrcode-terminal";

const apiUrl = (process.env.FIELDAPP_API_URL || "").replace(/\/$/, "");
const secret = process.env.WHATSAPP_WORKER_SECRET || "";
const recipients = (process.env.WHATSAPP_REPORT_RECIPIENTS || "").split(",").map(value => value.trim()).filter(Boolean);
const timezone = process.env.WHATSAPP_TIMEZONE || "Asia/Riyadh";
const authDir = process.env.WHATSAPP_AUTH_DIR || "./auth";
let socket;
const jidFor = value => value.includes("@") ? value : `${value.replace(/\D/g, "")}@s.whatsapp.net`;

// Render Web Services require a listening port. Background-worker deployments can omit PORT.
if (process.env.PORT) createServer((request, response) => { response.writeHead(request.url === "/health" ? 200 : 404, { "Content-Type": "text/plain" }); response.end(request.url === "/health" ? "ok" : "not found"); }).listen(Number(process.env.PORT), "0.0.0.0", () => console.log(`Health server listening on ${process.env.PORT}`));

if (!apiUrl || !secret || !recipients.length) throw new Error("FIELDAPP_API_URL و WHATSAPP_WORKER_SECRET و WHATSAPP_REPORT_RECIPIENTS مطلوبة");

async function connect() {
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  socket = makeWASocket({ auth: state, logger: pino({ level: "silent" }), markOnlineOnConnect: false });
  socket.ev.on("creds.update", saveCreds);
  socket.ev.on("connection.update", ({ connection, lastDisconnect, qr }) => {
    if (qr) qrcode.generate(qr, { small: true });
    if (connection === "open") {
      console.log("WhatsApp worker connected");
      socket.groupFetchAllParticipating().then(groups => {
        console.log("Available WhatsApp groups:");
        for (const group of Object.values(groups)) console.log(`${group.subject}: ${group.id}`);
      }).catch(error => console.error("تعذر قراءة المجموعات", error));
    }
    if (connection === "close") {
      const code = lastDisconnect?.error?.output?.statusCode;
      if (code !== DisconnectReason.loggedOut) setTimeout(connect, 5000);
      else console.error("WhatsApp session logged out; احذف مجلد auth وأعد مسح QR.");
    }
  });
}

async function getReport(period) {
  const response = await fetch(`${apiUrl}/internal/whatsapp-report?period=${period}`, { headers: { "x-whatsapp-worker-secret": secret } });
  if (!response.ok) throw new Error(`API report request failed: ${response.status}`);
  return response.json();
}

function formatReport(report) {
  const title = { daily: "يومي", weekly: "أسبوعي", monthly: "شهري", yearly: "سنوي" }[report.period];
  const lines = [`FieldApp — التقرير ${title}`, `الفترة: ${report.date_from} إلى ${report.date_to}`, `عدد المهام: ${report.tasks.length}`, ""];
  for (const task of report.tasks) lines.push(`• ${task.task_number} | ${task.technician_name} | ${task.city || "غير محدد"} | ${task.task_type} | ${task.task_status}`);
  return lines.join("\n").slice(0, 65000);
}

async function sendReport(period) {
  if (!socket?.user) return console.warn("WhatsApp غير متصل؛ تم تجاوز التقرير", period);
  const message = formatReport(await getReport(period));
  for (const recipient of recipients) await socket.sendMessage(jidFor(recipient), { text: message });
  console.log(`Sent ${period} report to ${recipients.length} recipient(s)`);
}

await connect();
cron.schedule(process.env.WHATSAPP_DAILY_CRON || "0 23 * * *", () => sendReport("daily").catch(console.error), { timezone });
cron.schedule(process.env.WHATSAPP_WEEKLY_CRON || "0 23 * * 6", () => sendReport("weekly").catch(console.error), { timezone });
cron.schedule(process.env.WHATSAPP_MONTHLY_CRON || "0 23 28 * *", () => sendReport("monthly").catch(console.error), { timezone });
cron.schedule(process.env.WHATSAPP_YEARLY_CRON || "0 23 31 12 *", () => sendReport("yearly").catch(console.error), { timezone });
