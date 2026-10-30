// Usage guard for the live AI routes, so a public demo cannot drain the API quota during judging.
// Per-instance memory: on serverless each warm instance counts separately, which is enough for a demo.
// AI_DAILY_LIMIT (all users) and AI_PER_IP_LIMIT (per visitor) come from the environment.

const day = () => new Date().toISOString().slice(0, 10);
let state = { day: day(), total: 0, perIp: new Map<string, number>() };

export function cekBatas(ip: string): { ok: true } | { ok: false; alasan: string } {
  if (process.env.AI_ENABLED === "false") return { ok: false, alasan: "Fitur AI sedang dimatikan." };
  if (state.day !== day()) state = { day: day(), total: 0, perIp: new Map() };
  const total = Number(process.env.AI_DAILY_LIMIT ?? 300);
  const perIp = Number(process.env.AI_PER_IP_LIMIT ?? 20);
  const used = state.perIp.get(ip) ?? 0;
  if (state.total >= total) return { ok: false, alasan: "Kuota AI harian untuk demo sudah habis. Coba lagi besok." };
  if (used >= perIp) return { ok: false, alasan: "Batas pemakaian AI untuk perangkat ini hari ini sudah tercapai." };
  state.total += 1;
  state.perIp.set(ip, used + 1);
  return { ok: true };
}

export function ipDari(req: Request): string {
  return req.headers.get("x-forwarded-for")?.split(",")[0].trim() || req.headers.get("x-real-ip") || "lokal";
}
