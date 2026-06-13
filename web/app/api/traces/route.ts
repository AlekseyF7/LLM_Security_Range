// Server-side proxy to the Langfuse public API for recent traces.
// SECURITY: LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are read ONLY here
// (server). They must never be exposed via NEXT_PUBLIC_*. Graceful fallback
// to {available:false} when keys are missing or Langfuse is unreachable.

type LangfuseTrace = { id?: string; name?: string; timestamp?: string };

export async function GET() {
  const host = process.env.LANGFUSE_HOST || "http://langfuse:3000";
  const pk = process.env.LANGFUSE_PUBLIC_KEY;
  const sk = process.env.LANGFUSE_SECRET_KEY;
  if (!pk || !sk) return Response.json({ available: false });

  try {
    const auth = Buffer.from(`${pk}:${sk}`).toString("base64");
    const resp = await fetch(`${host}/api/public/traces?limit=10`, {
      headers: { Authorization: `Basic ${auth}` },
      cache: "no-store",
    });
    if (!resp.ok) return Response.json({ available: false });
    const json = (await resp.json()) as { data?: LangfuseTrace[] };
    const data = json.data ?? [];
    return Response.json({
      available: true,
      traces: data.map((t) => ({ id: t.id ?? "", name: t.name ?? "trace", ts: t.timestamp ?? "" })),
    });
  } catch {
    return Response.json({ available: false });
  }
}
