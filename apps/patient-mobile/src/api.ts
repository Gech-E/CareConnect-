import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const API = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8005/api/v1";
const TOKEN_KEY = "careconnect_access_token";
// Native stores tokens in Keychain/Keystore. Web intentionally does not persist sensitive sessions.
let webToken: string | null = null;

export type Clinician = {
  id: string; first_name: string; last_name: string; credentials?: string | string[];
  profile_image_url?: string | null; average_rating?: number | null; review_count?: number;
  bio?: string; roles?: Array<{ specialty: string; languages?: string[]; price_range_min?: number | null }>;
};
export type Appointment = {
  id: string; practitioner_id: string; scheduled_start: string; scheduled_end: string;
  status: string; visit_type: string;
};

export const session = {
  async read(): Promise<string | null> {
    return Platform.OS === "web" ? webToken : SecureStore.getItemAsync(TOKEN_KEY);
  },
  async save(token: string) {
    if (Platform.OS === "web") webToken = token;
    else await SecureStore.setItemAsync(TOKEN_KEY, token);
  },
  async clear() {
    if (Platform.OS === "web") webToken = null;
    else await SecureStore.deleteItemAsync(TOKEN_KEY);
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(path: string, options: RequestInit = {}, authorized = false): Promise<T> {
  const token = authorized ? await session.read() : null;
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const error = await response.json();
      message = error?.error?.message ?? error?.detail ?? message;
      if (typeof message !== "string") message = "Please check your information.";
    } catch { /* Keep a safe fallback message. */ }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

type AuthResult = { tokens: { access_token: string }; role: string };
export const api = {
  specialties: () => request<Array<{name: string}>>("/specialties"),
  clinicians: (query = "", specialty = "") => request<{items: Clinician[]}>(
    `/practitioners?query=${encodeURIComponent(query)}&specialty=${encodeURIComponent(specialty)}`),
  clinician: (id: string) => request<Clinician>(`/practitioners/${encodeURIComponent(id)}`),
  availability: (id: string, start: string, end: string) =>
    request<{ availability: Record<string, Array<{ start: string; is_available: boolean }>> }>(
      `/practitioners/${encodeURIComponent(id)}/availability?start_date=${start}&end_date=${end}`),
  login: (email: string, password: string) => request<AuthResult>("/auth/login", {
    method: "POST", body: JSON.stringify({ email, password }),
  }),
  register: (email: string, password: string) => request<AuthResult>("/auth/register", {
    method: "POST", body: JSON.stringify({ email, password }),
  }),
  appointments: () => request<{ items: Appointment[] }>("/appointments", {}, true),
  hold: (practitioner_id: string, slot_start: string) =>
    request<{hold_id: string}>("/appointment-holds", {
      method: "POST", body: JSON.stringify({
        practitioner_id, slot_start, visit_type: "video",
        idempotency_key: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      }),
    }, true),
  confirm: (hold_id: string) => request<Appointment>("/appointments", {
    method: "POST", body: JSON.stringify({
      hold_id, idempotency_key: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    }),
  }, true),
  logout: () => request<void>("/auth/logout", {method: "POST"}, true),
};
