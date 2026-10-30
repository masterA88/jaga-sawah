// One Claude client for the live routes. Locally the SDK picks up the `ant auth login` profile; on Vercel it
// reads ANTHROPIC_API_KEY from the environment. The key never reaches the browser.
import Anthropic from "@anthropic-ai/sdk";

export const MODEL = "claude-opus-5-5";
export const client = new Anthropic();

export function pesanGalat(e: unknown): { status: number; pesan: string } {
  if (e instanceof Anthropic.RateLimitError) return { status: 429, pesan: "Layanan AI sedang sibuk. Coba lagi sebentar lagi." };
  if (e instanceof Anthropic.AuthenticationError) return { status: 500, pesan: "Kunci layanan AI belum diatur di server." };
  if (e instanceof Anthropic.APIError) return { status: 502, pesan: `Layanan AI menolak permintaan (${e.status}).` };
  // without ANTHROPIC_API_KEY the SDK throws a plain Error before any request is made
  if (e instanceof Error && /api.?key|auth/i.test(e.message)) return { status: 500, pesan: "Kunci layanan AI belum diatur di server." };
  return { status: 500, pesan: "Terjadi kesalahan di server." };
}
