"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  HeartPulse,
  LockKeyhole,
  LogOut,
  Search,
  Star,
  UserRound,
  Video,
} from "lucide-react";
import {
  api,
  ApiError,
  newBookingKey,
  SESSION_EXPIRED_EVENT,
  type Appointment,
  type Clinician,
  type Slot,
} from "../lib/api";
import { AuthDialog } from "./components/auth-dialog";
import { DoctorGrid, fullName } from "./components/doctor-grid";

type Page =
  "home" | "doctors" | "doctor" | "booking" | "appointments" | "account";
const shortDate = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
};
const format = (date: string) =>
  new Date(date).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

export default function PatientPage() {
  const [page, setPage] = useState<Page>("home");
  const [doctors, setDoctors] = useState<Clinician[]>([]);
  const [specialties, setSpecialties] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [doctor, setDoctor] = useState<Clinician | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [visits, setVisits] = useState<Appointment[]>([]);
  const [signedIn, setSignedIn] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const pageRequest = useRef<AbortController | null>(null);
  const searchRequest = useRef<AbortController | null>(null);
  const booking = useRef<{
    selection: string;
    key: string;
    holdId?: string;
  } | null>(null);
  const submitting = useRef(false);

  const navigate = (next: Page) => {
    pageRequest.current?.abort();
    setPage(next);
    setError("");
    setSuccess("");
    setLoading(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  };
  const getDoctors = useCallback(async () => {
    searchRequest.current?.abort();
    const controller = new AbortController();
    searchRequest.current = controller;
    setLoading(true);
    setError("");
    try {
      setDoctors(
        (await api.clinicians(query, specialty, controller.signal)).items,
      );
    } catch (e) {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "Unable to load clinicians.");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [query, specialty]);
  useEffect(() => {
    if (page !== "home" && page !== "doctors") return;
    const timer = window.setTimeout(() => void getDoctors(), 250);
    return () => {
      window.clearTimeout(timer);
      searchRequest.current?.abort();
    };
  }, [page, getDoctors]);
  useEffect(() => {
    const controller = new AbortController();
    api
      .specialties(controller.signal)
      .then((items) => setSpecialties(items.map((x) => x.name)))
      .catch(() => {});
    const expired = () => {
      setSignedIn(false);
      setVisits([]);
      booking.current = null;
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, expired);
    api
      .session(controller.signal)
      .then(() => setSignedIn(true))
      .catch((e) => {
        if (
          !controller.signal.aborted &&
          (!(e instanceof ApiError) || e.status !== 401)
        )
          setError("Could not restore your session. Please sign in again.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setCheckingSession(false);
      });
    return () => {
      controller.abort();
      pageRequest.current?.abort();
      window.removeEventListener(SESSION_EXPIRED_EVENT, expired);
    };
  }, []);
  useEffect(() => {
    if (page !== "appointments" || !signedIn) return;
    const controller = new AbortController();
    setLoading(true);
    api
      .appointments(controller.signal)
      .then((data) => setVisits(data.items))
      .catch((e) => {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "Could not load visits.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [page, signedIn]);

  async function chooseDoctor(item: Clinician) {
    setDoctor(item);
    navigate("doctor");
    const controller = new AbortController();
    pageRequest.current = controller;
    try {
      setDoctor(await api.clinician(item.id, controller.signal));
    } catch (e) {
      if (!controller.signal.aborted)
        setError(
          e instanceof Error ? e.message : "Could not load clinician details.",
        );
    }
  }
  async function viewSlots() {
    if (!doctor) return;
    navigate("booking");
    setSelectedSlot("");
    setSlots([]);
    setLoading(true);
    booking.current = null;
    const controller = new AbortController();
    pageRequest.current = controller;
    try {
      const result = await api.availability(
        doctor.id,
        shortDate(0),
        shortDate(7),
        controller.signal,
      );
      setSlots(
        Object.values(result.availability)
          .flat()
          .filter((s) => s.is_available && Date.parse(s.start) > Date.now())
          .sort((a, b) => Date.parse(a.start) - Date.parse(b.start)),
      );
    } catch (e) {
      if (!controller.signal.aborted)
        setError(
          e instanceof Error ? e.message : "Unable to load appointment times.",
        );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }
  async function book() {
    if (!doctor || !selectedSlot || submitting.current) return;
    if (!signedIn) {
      setAuthOpen(true);
      return;
    }
    submitting.current = true;
    setBusy(true);
    setError("");
    const selection = doctor.id + ":" + selectedSlot;
    if (booking.current?.selection !== selection)
      booking.current = { selection, key: newBookingKey() };
    const attempt = booking.current;
    try {
      if (!attempt.holdId)
        attempt.holdId = (
          await api.hold(doctor.id, selectedSlot, attempt.key)
        ).hold_id;
      await api.confirm(attempt.holdId, attempt.key);
      booking.current = null;
      navigate("appointments");
      setSuccess("Your appointment has been confirmed.");
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) booking.current = null;
      setError(
        e instanceof Error ? e.message : "Unable to confirm this appointment.",
      );
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  async function auth(email: string, password: string, register: boolean) {
    if (checkingSession || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setAuthError("");
    try {
      if (register) await api.register(email.trim(), password);
      else await api.login(email.trim(), password);
      setSignedIn(true);
      setAuthOpen(false);
      setError("");
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "Unable to authenticate.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  async function signOut() {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    let message = "";
    let cookieCleared = true;
    try {
      await api.logout();
    } catch (e) {
      cookieCleared = e instanceof ApiError && e.status === 503;
      message =
        e instanceof Error
          ? e.message
          : "The server could not complete sign out. Please retry.";
    } finally {
      if (cookieCleared) {
        setSignedIn(false);
        setVisits([]);
        booking.current = null;
      }
      if (message) setError(message);
      submitting.current = false;
      setBusy(false);
    }
  }
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="header">
        <div className="shell header-inner">
          <button
            className="logo"
            onClick={() => navigate("home")}
            aria-label="CareConnect home"
            style={{ border: 0, background: "none", padding: 0 }}
          >
            <span className="logo-icon">
              <HeartPulse size={21} />
            </span>
            care<mark>connect</mark>
          </button>
          <nav className="nav" aria-label="Main navigation">
            {(
              [
                ["home", "Home"],
                ["doctors", "Find care"],
                ["appointments", "Appointments"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                className={page === key ? "active" : ""}
                onClick={() => navigate(key)}
                aria-current={page === key ? "page" : undefined}
              >
                {label}
              </button>
            ))}
          </nav>
          <button className="account" onClick={() => navigate("account")}>
            <UserRound size={17} />{" "}
            <span>{signedIn ? "My account" : "Sign in"}</span>
          </button>
        </div>
      </header>
      <main
        id="main-content"
        className="shell layout"
        aria-busy={checkingSession}
      >
        {checkingSession && (
          <p role="status" className="sub">
            Checking your session…
          </p>
        )}
        {page === "home" && (
          <>
            <section className="hero">
              <div className="hero-copy">
                <span className="eyebrow">CARE, ON YOUR SCHEDULE</span>
                <h1>
                  Find care.
                  <br />
                  Book a visit.
                </h1>
                <p>Choose your clinician and a time that works for you.</p>
                <div className="hero-actions">
                  <button className="btn" onClick={() => navigate("doctors")}>
                    Find care <ArrowRight size={18} />
                  </button>
                  <button
                    className="btn ghost"
                    onClick={() => navigate("appointments")}
                  >
                    My appointments
                  </button>
                </div>
              </div>
              <div className="hero-art" aria-hidden="true">
                <div className="hero-orb">
                  <HeartPulse />
                </div>
              </div>
            </section>
            <div className="section-heading">
              <h2 className="section-title">Our clinicians</h2>
              <button className="link" onClick={() => navigate("doctors")}>
                View all <ArrowRight size={15} />
              </button>
            </div>
            {loading ? (
              <p className="loading" role="status">
                Loading clinicians…
              </p>
            ) : error ? (
              <p className="error" role="alert">
                {error}{" "}
                <button className="link" onClick={() => void getDoctors()}>
                  Retry
                </button>
              </p>
            ) : (
              <DoctorGrid
                doctors={doctors.slice(0, 3)}
                onSelect={chooseDoctor}
              />
            )}
          </>
        )}
        {page === "doctors" && (
          <>
            <h1 className="title">Find care</h1>

            <div className="searchline">
              <label className="searchbox">
                <Search size={19} color="#6b7d87" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search clinicians"
                  aria-label="Search clinicians by name"
                />
              </label>
              <select
                className="select"
                value={specialty}
                onChange={(e) => setSpecialty(e.target.value)}
                aria-label="Filter by specialty"
              >
                <option value="">All specialties</option>
                {specialties.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            {loading ? (
              <p className="loading" role="status">
                Finding clinicians…
              </p>
            ) : error ? (
              <div className="error" role="alert">
                {error}
                <div>
                  <button className="link" onClick={() => void getDoctors()}>
                    Try again
                  </button>
                </div>
              </div>
            ) : (
              <DoctorGrid doctors={doctors} onSelect={chooseDoctor} />
            )}
          </>
        )}
        {(page === "doctor" || page === "booking") && doctor && (
          <>
            <button
              className="back"
              onClick={() =>
                navigate(page === "booking" ? "doctor" : "doctors")
              }
            >
              <ArrowLeft size={17} /> Back to{" "}
              {page === "booking" ? "profile" : "clinicians"}
            </button>

            <h1 className="title">
              {page === "booking" ? "Choose a time" : fullName(doctor)}
            </h1>
            {page === "doctor" ? (
              <div className="profile-grid">
                <div className="card">
                  <div className="avatar" style={{ width: 88, height: 88 }}>
                    <UserRound size={43} />
                  </div>

                  <p className="lead">
                    {doctor.roles?.map((x) => x.specialty).join(" · ") ||
                      "Healthcare professional"}
                  </p>
                  {(doctor.review_count ?? 0) > 0 && (
                    <p className="rating">
                      <Star size={17} fill="currentColor" />
                      {doctor.average_rating} · {doctor.review_count} reviews
                    </p>
                  )}
                  {doctor.bio && <p className="lead">{doctor.bio}</p>}
                </div>
                <aside className="card">
                  <h2 style={{ marginTop: 0 }}>Book a video visit</h2>
                  <button className="btn" onClick={() => void viewSlots()}>
                    See times <ArrowRight size={17} />
                  </button>
                </aside>
              </div>
            ) : (
              <div className="profile-grid">
                <section className="card">
                  <h2 style={{ marginTop: 0 }}>Available times</h2>
                  <p className="sub">Next 7 days · Your local timezone</p>
                  {loading ? (
                    <p className="loading" role="status">
                      Loading availability…
                    </p>
                  ) : slots.length ? (
                    <div className="slot-grid">
                      {slots.map((s) => (
                        <button
                          key={s.start}
                          className={`slot ${selectedSlot === s.start ? "selected" : ""}`}
                          onClick={() => setSelectedSlot(s.start)}
                          aria-pressed={selectedSlot === s.start}
                        >
                          {format(s.start)}
                        </button>
                      ))}
                    </div>
                  ) : !error ? (
                    <p className="empty">
                      No available slots in the next seven days.
                    </p>
                  ) : null}
                </section>
                <aside className="card">
                  <p className="eyebrow">APPOINTMENT SUMMARY</p>
                  <h2>{fullName(doctor)}</h2>
                  <p className="sub">
                    {doctor.roles?.[0]?.specialty || "Virtual consultation"}
                  </p>
                  <div className="list-item">
                    <span>Visit type</span>
                    <strong>
                      <Video size={16} style={{ verticalAlign: "middle" }} />{" "}
                      Video
                    </strong>
                  </div>
                  <div className="list-item">
                    <span>When</span>
                    <strong>
                      {selectedSlot ? format(selectedSlot) : "Select a time"}
                    </strong>
                  </div>
                  <br />
                  <button
                    className="btn"
                    onClick={() => void book()}
                    disabled={!selectedSlot || busy || checkingSession}
                  >
                    {busy
                      ? "Confirming…"
                      : signedIn
                        ? "Confirm appointment"
                        : "Sign in to book"}{" "}
                    <ArrowRight size={17} />
                  </button>
                </aside>
              </div>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
          </>
        )}
        {page === "appointments" && (
          <>
            <h1 className="title">My appointments</h1>

            {success && (
              <div className="notice" role="status">
                <CheckCircle2 size={17} style={{ verticalAlign: "middle" }} />{" "}
                {success}
              </div>
            )}
            {!signedIn ? (
              <section
                className="card"
                style={{ maxWidth: 540, marginTop: 24 }}
              >
                <LockKeyhole color="#0a807c" size={32} />
                <h2>Sign in to see your visits</h2>

                <button
                  className="btn"
                  disabled={checkingSession}
                  onClick={() => setAuthOpen(true)}
                >
                  Sign in <ArrowRight size={17} />
                </button>
              </section>
            ) : (
              <section className="card" style={{ marginTop: 24 }}>
                {loading ? (
                  <p className="loading">Loading appointments…</p>
                ) : visits.length ? (
                  visits.map((v) => (
                    <div className="list-item" key={v.id}>
                      <div>
                        <strong>{format(v.scheduled_start)}</strong>
                        <p className="sub">
                          <Video
                            size={15}
                            style={{ verticalAlign: "middle" }}
                          />{" "}
                          {v.visit_type === "audio"
                            ? "Audio visit"
                            : "Video visit"}
                        </p>
                      </div>
                      <span className="badge">
                        {v.status.replaceAll("_", " ")}
                      </span>
                    </div>
                  ))
                ) : !error ? (
                  <div className="empty">
                    <CalendarDays size={35} style={{ margin: "0 auto 10px" }} />
                    <p>No appointments yet.</p>
                    <button
                      className="btn secondary"
                      onClick={() => navigate("doctors")}
                    >
                      Find a clinician
                    </button>
                  </div>
                ) : null}
                {error && (
                  <p className="error" role="alert">
                    {error}
                  </p>
                )}
              </section>
            )}
          </>
        )}
        {page === "account" && (
          <>
            <h1 className="title">Account</h1>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <div className="card" style={{ maxWidth: 610, marginTop: 20 }}>
              <div className="avatar">
                <UserRound size={30} />
              </div>
              <h2>{signedIn ? "Patient account" : "Welcome to CareConnect"}</h2>
              <p className="lead">
                {signedIn
                  ? "You are signed in."
                  : "Sign in to book and manage visits."}
              </p>
              <button
                className="btn"
                disabled={busy || checkingSession}
                onClick={() => (signedIn ? void signOut() : setAuthOpen(true))}
              >
                {signedIn ? (
                  <>
                    <LogOut size={17} /> Sign out
                  </>
                ) : (
                  <>
                    <LockKeyhole size={17} /> Sign in or register
                  </>
                )}
              </button>
            </div>
          </>
        )}
      </main>
      <footer className="footer">
        <div className="shell">
          <HeartPulse size={16} style={{ verticalAlign: "middle" }} />{" "}
          CareConnect · Preview — no real patient data or emergency care.
        </div>
      </footer>
      {authOpen && (
        <AuthDialog
          busy={busy}
          error={authError}
          onSubmit={auth}
          onClose={() => {
            if (!busy) {
              setAuthOpen(false);
              setAuthError("");
            }
          }}
          onModeChange={() => setAuthError("")}
        />
      )}
    </>
  );
}
