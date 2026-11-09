import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const SAFE_SEGMENT = /^[A-Za-z0-9_-]+$/;

/** Server-side proxy: /api/<path> -> ${BACKEND_URL}/api/<path> (resolved at runtime). */
async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  if (!path.every((s) => SAFE_SEGMENT.test(s))) {
    return NextResponse.json({ detail: "Invalid path" }, { status: 400 });
  }
  const backend = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const target = `${backend}/api/${path.join("/")}${req.nextUrl.search}`;
  try {
    const body = req.method === "POST" ? await req.text() : undefined;
    const res = await fetch(target, {
      method: req.method,
      headers: body ? { "content-type": req.headers.get("content-type") ?? "application/json" } : undefined,
      body,
      cache: "no-store",
    });
    return new NextResponse(await res.text(), {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch (err) {
    return NextResponse.json(
      { detail: `Backend unreachable: ${err instanceof Error ? err.message : String(err)}` },
      { status: 502 },
    );
  }
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, ctx);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, ctx);
}
