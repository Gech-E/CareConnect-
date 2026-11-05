import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, request } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("browser API client", () => {
  it("preserves the booking idempotency key across retries", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(Response.json({ hold_id: "hold" }));
    vi.stubGlobal("fetch", fetchMock);
    await api.hold("practitioner", "2027-01-01T08:00:00Z", "stable-key");
    fetchMock.mockResolvedValue(Response.json({ hold_id: "hold" }));
    await api.hold("practitioner", "2027-01-01T08:00:00Z", "stable-key");
    for (const [url, options] of fetchMock.mock.calls) {
      expect(url).toBe("/api/care/appointment-holds");
      expect(JSON.parse(options.body).idempotency_key).toBe("stable-key");
      expect(new Headers(options.headers).has("Authorization")).toBe(false);
      expect(options.credentials).toBe("same-origin");
    }
  });
  it("reports malformed successful responses as a recoverable API error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("bad gateway")),
    );
    await expect(request("/specialties")).rejects.toBeInstanceOf(ApiError);
  });
  it("notifies UI about revoked sessions but not failed login attempts", async () => {
    const events = new EventTarget();
    const listener = vi.fn();
    events.addEventListener("careconnect:session-expired", listener);
    vi.stubGlobal("window", events);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementation(() =>
          Promise.resolve(
            Response.json({ error: { message: "Expired" } }, { status: 401 }),
          ),
        ),
    );
    await expect(
      api.login("person@example.com", "wrong-password"),
    ).rejects.toBeInstanceOf(ApiError);
    expect(listener).not.toHaveBeenCalled();
    await expect(api.appointments()).rejects.toBeInstanceOf(ApiError);
    expect(listener).toHaveBeenCalledOnce();
  });
});
