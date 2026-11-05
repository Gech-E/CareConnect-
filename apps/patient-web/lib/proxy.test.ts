import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { proxyRequest } from "./proxy";

const fetchMock = vi.fn<typeof fetch>();
const origin = "https://care.example";

function request(
  path: string,
  method = "GET",
  options: { origin?: string; cookie?: string; body?: string } = {},
) {
  const headers: Record<string, string> = {
    "content-type": "application/json",
  };
  if (options.origin) headers.origin = options.origin;
  if (options.cookie) headers.cookie = options.cookie;
  return new NextRequest(`${origin}/api/care/${path}`, {
    method,
    headers,
    body: options.body,
  });
}

beforeEach(() => {
  vi.stubEnv("NODE_ENV", "production");
  vi.stubEnv("CARECONNECT_API_URL", "https://api.example/api/v1");
  vi.stubEnv("CARECONNECT_WEB_ORIGIN", origin);
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("patient BFF security boundary", () => {
  it.each([undefined, "https://evil.example"])(
    "rejects mutations from origin %s before contacting the API",
    async (source) => {
      const response = await proxyRequest(
        request("auth/login", "POST", { origin: source, body: "{}" }),
        ["auth", "login"],
      );
      expect(response.status).toBe(403);
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );
  it("does not proxy arbitrary or privileged routes", async () => {
    const response = await proxyRequest(request("admin/users"), [
      "admin",
      "users",
    ]);
    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("requires the secure cookie for private data", async () => {
    const response = await proxyRequest(request("appointments"), [
      "appointments",
    ]);
    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("sets an HttpOnly secure cookie and never returns tokens to browser code", async () => {
    fetchMock.mockResolvedValue(
      Response.json({
        role: "patient",
        email: "person@example.com",
        tokens: {
          access_token: "secret-access",
          refresh_token: "secret-refresh",
          expires_in: 900,
        },
      }),
    );
    const response = await proxyRequest(
      request("auth/login", "POST", { origin, body: "{}" }),
      ["auth", "login"],
    );
    expect(await response.json()).toEqual({
      role: "patient",
      email: "person@example.com",
    });
    const cookie = response.headers.get("set-cookie");
    expect(cookie).toContain("__Host-careconnect-session=secret-access");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("Secure");
    expect(cookie).toContain("SameSite=strict");
    expect(cookie).not.toContain("secret-refresh");
    expect(response.headers.get("cache-control")).toBe("no-store");
  });
  it("forwards only cookie auth and strips profile data from the session response", async () => {
    fetchMock.mockResolvedValue(
      Response.json({
        role: "patient",
        email: "person@example.com",
        profile: { medical: "private" },
      }),
    );
    const response = await proxyRequest(
      request("session", "GET", { cookie: "__Host-careconnect-session=token" }),
      ["session"],
    );
    expect(await response.json()).toEqual({
      role: "patient",
      email: "person@example.com",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example/api/v1/me/",
      expect.objectContaining({ redirect: "error", cache: "no-store" }),
    );
    const headers = new Headers(fetchMock.mock.calls[0][1]?.headers);
    expect(headers.get("Authorization")).toBe("Bearer token");
  });
  it("clears the cookie after server-side session revocation", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "expired" }, { status: 401 }),
    );
    const response = await proxyRequest(
      request("appointments", "GET", {
        cookie: "__Host-careconnect-session=token",
      }),
      ["appointments"],
    );
    expect(response.status).toBe(401);
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
  });
  it("clears browser auth even if upstream logout is unavailable", async () => {
    fetchMock.mockRejectedValue(new Error("unavailable"));
    const response = await proxyRequest(
      request("auth/logout", "POST", {
        origin,
        cookie: "__Host-careconnect-session=token",
      }),
      ["auth", "logout"],
    );
    expect(response.status).toBe(503);
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
  });
  it("does not echo validation inputs or internal server messages", async () => {
    fetchMock.mockResolvedValue(
      Response.json(
        {
          detail: [{ input: "secret-password" }],
          error: { message: "database-password" },
        },
        { status: 422 },
      ),
    );
    const response = await proxyRequest(
      request("auth/register", "POST", { origin, body: "{}" }),
      ["auth", "register"],
    );
    expect(response.status).toBe(422);
    expect(await response.text()).not.toMatch(
      /secret-password|database-password/,
    );
  });
  it("rejects oversized request bodies", async () => {
    const response = await proxyRequest(
      request("auth/register", "POST", {
        origin,
        body: JSON.stringify({ value: "x".repeat(17000) }),
      }),
      ["auth", "register"],
    );
    expect(response.status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("fails closed when production origin is missing", async () => {
    vi.stubEnv("CARECONNECT_WEB_ORIGIN", "");
    const response = await proxyRequest(request("specialties"), [
      "specialties",
    ]);
    expect(response.status).toBe(503);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
