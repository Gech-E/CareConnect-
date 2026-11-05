import { NextRequest, NextResponse } from "next/server";

const MAX_BODY_BYTES = 16_384;
const UUID = "[0-9a-fA-F-]{36}";
const PUBLIC_GET = new RegExp(
  `^(specialties|practitioners|practitioners/${UUID}(/availability)?)$`,
);
const AUTH_POST = /^auth\/(login|register)$/;
const PRIVATE_GET = /^(session|appointments)$/;
const PRIVATE_POST = /^(appointment-holds|appointments|auth\/logout)$/;

function configuration() {
  const production = process.env.NODE_ENV === "production";
  const api =
    process.env.CARECONNECT_API_URL ||
    (!production ? "http://localhost:8005/api/v1" : "");
  const origin =
    process.env.CARECONNECT_WEB_ORIGIN ||
    (!production ? "http://localhost:3005" : "");
  const apiUrl = new URL(api);
  const webUrl = new URL(origin);
  if (
    !["http:", "https:"].includes(apiUrl.protocol) ||
    apiUrl.username ||
    apiUrl.password ||
    apiUrl.search ||
    apiUrl.hash ||
    !["http:", "https:"].includes(webUrl.protocol) ||
    webUrl.origin !== origin ||
    (production && webUrl.protocol !== "https:")
  ) {
    throw new Error("Invalid server configuration");
  }
  return {
    api: api.replace(/\/$/, ""),
    origin,
    production,
    cookie: production ? "__Host-careconnect-session" : "careconnect-session",
  };
}

function json(data: unknown, status = 200) {
  return NextResponse.json(data, {
    status,
    headers: { "Cache-Control": "no-store", Pragma: "no-cache" },
  });
}

function error(status: number, message: string) {
  return json({ error: { message } }, status);
}

async function readBody(request: NextRequest) {
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    return error(415, "Send the request as JSON.");
  }
  const reader = request.body?.getReader();
  if (!reader) return error(400, "A request body is required.");
  let size = 0;
  const chunks: Uint8Array[] = [];
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > MAX_BODY_BYTES) {
      await reader.cancel();
      return error(413, "The request is too large.");
    }
    chunks.push(value);
  }
  try {
    const body = Buffer.concat(chunks).toString("utf8");
    JSON.parse(body);
    return body;
  } catch {
    return error(400, "The request contains invalid JSON.");
  }
}

/** A narrowly scoped BFF: browser code never receives or stores bearer tokens. */
export async function proxyRequest(request: NextRequest, segments: string[]) {
  let config: ReturnType<typeof configuration>;
  try {
    config = configuration();
  } catch {
    return error(503, "The service is not configured. Please try again later.");
  }

  const path = segments.join("/");
  const isGet = request.method === "GET";
  const isAuth = request.method === "POST" && AUTH_POST.test(path);
  const isPrivate = isGet ? PRIVATE_GET.test(path) : PRIVATE_POST.test(path);
  if (
    !(isGet && PUBLIC_GET.test(path)) &&
    !isAuth &&
    !(request.method === "POST" && isPrivate) &&
    !(isGet && isPrivate)
  ) {
    return error(404, "This endpoint is not available.");
  }
  // SameSite is defense in depth; an exact trusted Origin is required on every mutation,
  // including login, to prevent login CSRF. Never trust incoming Host/forwarded headers.
  if (!isGet && request.headers.get("origin") !== config.origin) {
    return error(403, "The request origin is not allowed.");
  }

  const token = request.cookies.get(config.cookie)?.value;
  const clearCookie = (response: NextResponse) => {
    response.cookies.set(config.cookie, "", {
      httpOnly: true,
      secure: config.production,
      sameSite: "strict",
      path: "/",
      maxAge: 0,
    });
    return response;
  };
  if (isPrivate && !token) {
    return path === "auth/logout"
      ? clearCookie(json({ signedOut: true }))
      : error(401, "Please sign in to continue.");
  }
  let body: string | undefined;
  if (!isGet && path !== "auth/logout") {
    const result = await readBody(request);
    if (result instanceof NextResponse) return result;
    body = result;
  }
  const headers = new Headers({ Accept: "application/json" });
  if (body) headers.set("Content-Type", "application/json");
  if (isPrivate && token) headers.set("Authorization", `Bearer ${token}`);
  let upstream: Response;
  try {
    const query = isGet && path !== "session" ? request.nextUrl.search : "";
    upstream = await fetch(
      `${config.api}/${path === "session" ? "me/" : path}${query}`,
      {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(15_000),
      },
    );
  } catch {
    const response = error(
      503,
      "The care service is temporarily unavailable. Please try again.",
    );
    return path === "auth/logout" ? clearCookie(response) : response;
  }

  if (path === "auth/logout") {
    return clearCookie(
      upstream.ok || upstream.status === 401
        ? json({ signedOut: true })
        : error(
            503,
            "You are signed out on this device. The server could not revoke other sessions.",
          ),
    );
  }
  if (!upstream.ok) {
    // Never forward validation inputs, stack traces, or arbitrary upstream response bodies.
    let message =
      upstream.status === 422
        ? "Please check the information you entered."
        : "The request could not be completed.";
    if (upstream.status === 401)
      message = isAuth
        ? "Invalid email or password."
        : "Your session has expired. Please sign in again.";
    if (upstream.status === 409)
      message = isAuth
        ? "Registration could not be completed. Try signing in."
        : "That appointment time is no longer available. Please choose another time.";
    if (upstream.status === 429)
      message = "Too many requests. Please wait and try again.";
    if (upstream.status >= 500)
      message =
        "The care service is temporarily unavailable. Please try again.";
    const response = error(upstream.status, message);
    return isPrivate && upstream.status === 401
      ? clearCookie(response)
      : response;
  }
  let data;
  try {
    data = await upstream.json();
  } catch {
    return error(502, "The care service returned an invalid response.");
  }
  if (isAuth) {
    if (data?.role !== "patient")
      return error(403, "Please use a patient account.");
    const { access_token: accessToken, expires_in: expiresIn } =
      data.tokens ?? {};
    if (
      typeof accessToken !== "string" ||
      !accessToken ||
      !Number.isSafeInteger(expiresIn) ||
      expiresIn <= 0
    ) {
      return error(
        502,
        "The care service returned an invalid sign-in response.",
      );
    }
    const response = json(
      { role: data.role, email: data.email },
      upstream.status,
    );
    // Intentionally do not persist refresh tokens. Session expiry requires reauthentication.
    response.cookies.set(config.cookie, accessToken, {
      httpOnly: true,
      secure: config.production,
      sameSite: "strict",
      path: "/",
      maxAge: expiresIn,
    });
    return response;
  }
  if (path === "session") {
    if (data?.role !== "patient")
      return clearCookie(error(403, "Please use a patient account."));
    return json({ role: data.role, email: data.email });
  }
  return json(data, upstream.status);
}
