// Browser session is kept in memory to avoid exposing bearer tokens through localStorage.
// Refreshing the page signs the user out. Production should use an audited BFF with
// HttpOnly, Secure, SameSite cookies and CSRF protections.
const BASE = (process.env.NEXT_PUBLIC_CARECONNECT_API_URL ?? "http://localhost:8005/api/v1").replace(/\/$/, "");
let token: string | null = null;

export type Clinician = {
  id: string;
  first_name: string;
  last_name: string;
  credentials?: string | string[] | null;
  bio?: string | null;
  average_rating?: number | null;
  review_count?: number | null;
  roles?: Array<{ specialty: string; languages?: string[]; price_range_min?: number | null }>;
};
export type Slot = { start: string; end?: string; is_available: boolean };
export type Appointment = { id: string; practitioner_id: string; scheduled_start: string; status: string; visit_type: string };
export const session = {
  set(next: string) { token = next; },
  active() { return !!token; },
  clear() { token = null; }
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(path: string, options: RequestInit = {}, auth = false): Promise<T> {
  if (auth && !token) throw new ApiError(401, "Please sign in to continue.");
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body) headers.set("Content-Type", "application/json");
  if (auth && token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { ...options, headers, cache: "no-store" });
  } catch {
    throw new ApiError(0, "Could not reach the server. Check that the API is running and try again.");
  }
  if (!response.ok) {
    let message = "The request could not be completed.";
    try {
      const data = await response.json();
      message = typeof data?.error?.message === "string" ? data.error.message
        : typeof data?.detail === "string" ? data.detail : message;
    } catch { /* Keep generic message */ }
    if (response.status === 401) session.clear();
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}
const post = (data: unknown) => ({ method: "POST", body: JSON.stringify(data) });
const key = () => typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

type AuthResult = { role: string; tokens: { access_token: string } };

export const api = {
  specialties: () => request<Array<{ name: string }>>("/specialties"),
  clinicians: (query = "", specialty = "") => request<{ items: Clinician[] }>(`/practitioners?query=${encodeURIComponent(query)}&specialty=${encodeURIComponent(specialty)}`),
  clinician: (id: string) => request<Clinician>(`/practitioners/${encodeURIComponent(id)}`),
  availability: (id: string, from: string, to: string) => request<{ availability: Record<string, Slot[]> }>(`/practitioners/${encodeURIComponent(id)}/availability?start_date=${from}&end_date=${to}`),
  appointments: () => request<{ items: Appointment[] }>("/appointments", {}, true),
  login: (email: string, password: string) => request<AuthResult>("/auth/login", post({ email, password })),
  register: (email: string, password: string) => request<AuthResult>("/auth/register", post({ email, password })),
  hold: (practitioner_id: string, slot_start: string) => request<{ hold_id: string }>("/appointment-holds", post({ practitioner_id, slot_start, visit_type: "video", idempotency_key: key() }), true),
  confirm: (hold_id: string) => request<Appointment>("/appointments", post({ hold_id, idempotency_key: key() }), true),
  logout: () => request<void>("/auth/logout", { method: "POST" }, true)
};
