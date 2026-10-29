import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const SAFE_SEGMENT = /^[A-Za-z0-9_-]+$/;

/** Server-side proxy: /api/<path> -> ${BACKEND_URL}/api/<path> (resolved at runtime). */
export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  if (!path.every((s) => SAFE_SEGMENT.test(s))) {
    return NextResponse.json({ detail: "Invalid path" }, { status: 400 });
  }
  const backend = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const target = `${backend}/api/${path.join("/")}${req.nextUrl.search}`;
  try {
    const res = await fetch(target, { cache: "no-store" });
    return new NextResponse(await res.text(), {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch (err) {
    return NextResponse.json({ detail: `Backend unreachable: ${(err as Error).message}` }, { status: 502 });
  }
}
