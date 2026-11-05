/** Browser client for the same-origin BFF. Authentication is held in an HttpOnly cookie. */
const BASE = "/api/care";
export const SESSION_EXPIRED_EVENT = "careconnect:session-expired";

export type Clinician = {
  id: string;
  first_name: string;
  last_name: string;
  credentials?: string | string[] | null;
  bio?: string | null;
  average_rating?: number | null;
  review_count?: number | null;
  roles?: Array<{
    specialty: string;
    languages?: string[];
    price_range_min?: number | null;
  }>;
};
export type Slot = { start: string; end?: string; is_available: boolean };
export type Appointment = {
  id: string;
  practitioner_id: string;
  scheduled_start: string;
  status: string;
  visit_type: string;
};
export type PatientSession = { role: "patient"; email: string };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = false,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...options,
      headers,
      credentials: "same-origin",
      cache: "no-store",
      signal: options.signal
        ? AbortSignal.any([options.signal, AbortSignal.timeout(20_000)])
        : AbortSignal.timeout(20_000),
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      0,
      "Could not reach the care service. Please try again.",
    );
  }
  if (!response.ok) {
    let message = "The request could not be completed.";
    try {
      const data = await response.json();
      if (typeof data?.error?.message === "string")
        message = data.error.message;
    } catch {
      /* Keep a safe generic error when the service does not return JSON. */
    }
    if (auth && response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      502,
      "The care service returned an invalid response. Please try again.",
    );
  }
}

const post = (data: unknown) => ({
  method: "POST",
  body: JSON.stringify(data),
});
export const newBookingKey = () => crypto.randomUUID();

export const api = {
  session: (signal?: AbortSignal) =>
    request<PatientSession>("/session", { signal }, true),
  specialties: (signal?: AbortSignal) =>
    request<Array<{ name: string }>>("/specialties", { signal }),
  clinicians: (query = "", specialty = "", signal?: AbortSignal) =>
    request<{ items: Clinician[] }>(
      `/practitioners?query=${encodeURIComponent(query)}&specialty=${encodeURIComponent(specialty)}`,
      { signal },
    ),
  clinician: (id: string, signal?: AbortSignal) =>
    request<Clinician>(`/practitioners/${encodeURIComponent(id)}`, { signal }),
  availability: (id: string, from: string, to: string, signal?: AbortSignal) =>
    request<{ availability: Record<string, Slot[]> }>(
      `/practitioners/${encodeURIComponent(id)}/availability?start_date=${encodeURIComponent(from)}&end_date=${encodeURIComponent(to)}`,
      { signal },
    ),
  appointments: (signal?: AbortSignal) =>
    request<{ items: Appointment[] }>("/appointments", { signal }, true),
  login: (email: string, password: string) =>
    request<PatientSession>("/auth/login", post({ email, password })),
  register: (email: string, password: string) =>
    request<PatientSession>("/auth/register", post({ email, password })),
  hold: (
    practitioner_id: string,
    slot_start: string,
    idempotency_key: string,
  ) =>
    request<{ hold_id: string }>(
      "/appointment-holds",
      post({
        practitioner_id,
        slot_start,
        visit_type: "video",
        idempotency_key,
      }),
      true,
    ),
  confirm: (hold_id: string, idempotency_key: string) =>
    request<Appointment>(
      "/appointments",
      post({ hold_id, idempotency_key }),
      true,
    ),
  logout: () => request<void>("/auth/logout", { method: "POST" }, true),
};
