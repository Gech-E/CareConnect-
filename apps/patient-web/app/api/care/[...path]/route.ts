import { NextRequest } from "next/server";
import { proxyRequest } from "../../../../lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: Context) {
  return proxyRequest(request, (await context.params).path);
}

export async function POST(request: NextRequest, context: Context) {
  return proxyRequest(request, (await context.params).path);
}
