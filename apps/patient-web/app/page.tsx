"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, ArrowLeft, ArrowRight, CalendarDays, CheckCircle2, ChevronRight, Clock3, HeartPulse, LockKeyhole, LogOut, Menu, MessageCircle, Search, ShieldCheck, Star, Stethoscope, UserRound, Video, X } from "lucide-react";
import { api, type Appointment, type Clinician, type Slot, session } from "../lib/api";

type Page = "home" | "doctors" | "doctor" | "booking" | "appointments" | "account";
const shortDate = (n: number) => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const format = (date: string) => new Date(date).toLocaleString(undefined, { weekday:"short", month:"short", day:"numeric", hour:"numeric", minute:"2-digit" });
const fullName = (d: Clinician) => `Dr. ${d.first_name} ${d.last_name}`;

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
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const navigate = (next: Page) => { setPage(next); setError(""); setSuccess(""); window.scrollTo({top:0,behavior:"smooth"}); };
  const getDoctors = useCallback(async () => {
    setLoading(true); setError("");
    try { setDoctors((await api.clinicians(query, specialty)).items); }
    catch(e) { setError(e instanceof Error ? e.message : "Unable to load clinicians."); }
    finally { setLoading(false); }
  }, [query, specialty]);
  useEffect(() => { if(page === "home" || page === "doctors") void getDoctors(); }, [page, getDoctors]);
  useEffect(() => { api.specialties().then(items => setSpecialties(items.map(x=>x.name))).catch(()=>{}); }, []);
  useEffect(() => {
    if(page !== "appointments" || !signedIn) return;
    setLoading(true);
    api.appointments().then(data=>setVisits(data.items)).catch(e=>setError(e instanceof Error ? e.message : "Could not load visits.")).finally(()=>setLoading(false));
  }, [page, signedIn]);
  async function chooseDoctor(item: Clinician) {
    setDoctor(item); navigate("doctor");
    try { setDoctor(await api.clinician(item.id)); }
    catch(e) { setError(e instanceof Error ? e.message : "Could not load clinician details."); }
  }
  async function viewSlots() {
    if (!doctor) return;
    navigate("booking"); setSelectedSlot(""); setSlots([]); setLoading(true);
    try {
      const result = await api.availability(doctor.id, shortDate(0), shortDate(7));
      setSlots(Object.values(result.availability).flat().filter(s=>s.is_available && Date.parse(s.start) > Date.now()));
    } catch(e) { setError(e instanceof Error ? e.message : "Unable to load appointment times."); }
    finally { setLoading(false); }
  }
  async function book() {
    if (!doctor || !selectedSlot) return;
    if (!signedIn) { setAuthOpen(true); return; }
    setBusy(true); setError("");
    try {
      const held = await api.hold(doctor.id,selectedSlot);
      await api.confirm(held.hold_id);
      navigate("appointments"); setSuccess("Your appointment has been confirmed.");
    } catch(e) { setError(e instanceof Error ? e.message : "Unable to confirm this appointment."); }
    finally { setBusy(false); }
  }
  async function auth() {
    setError("");
    if (!email.includes("@") || !password) { setError("Enter a valid email address and password."); return; }
    if(register && password.length < 12) { setError("Passwords must be at least 12 characters long."); return; }
    setBusy(true);
    try {
      const result = register ? await api.register(email,password) : await api.login(email,password);
      if (result.role !== "patient") throw new Error("Please use a patient account.");
      session.set(result.tokens.access_token); setSignedIn(true); setAuthOpen(false); setPassword("");
    } catch(e) { setError(e instanceof Error ? e.message : "Unable to authenticate."); }
    finally { setBusy(false); }
  }
  async function signOut() {
    try { await api.logout(); } catch { /* Always clear local session. */ }
    session.clear(); setSignedIn(false); setVisits([]); navigate("home");
  }
  return <>
    <header className="header"><div className="shell header-inner">
      <button className="logo" onClick={()=>navigate("home")} aria-label="CareConnect home" style={{border:0,background:"none",padding:0}}><span className="logo-icon"><HeartPulse size={21}/></span>care<mark>connect</mark></button>
      <nav className="nav" aria-label="Main navigation">
        {([["home","Home"],["doctors","Find care"],["appointments","Appointments"]] as const).map(([key,label])=><button key={key} className={page===key?"active":""} onClick={()=>navigate(key)}>{label}</button>)}
      </nav>
      <button className="account" onClick={()=>navigate("account")}><UserRound size={17}/> <span>{signedIn?"My account":"Sign in"}</span></button>
    </div></header>
    <main className="shell layout">
      {page==="home" && <>
        <div className="eyebrow">WELCOME TO CARECONNECT</div>
        <section className="hero">
          <div className="hero-copy"><span className="eyebrow">YOUR HEALTH, OUR PRIORITY</span><h1>Healthcare that feels a little more human.</h1><p>Find the right clinician, book a convenient time, and take the next step in your care—all in one place.</p><button className="btn" onClick={()=>navigate("doctors")}>Find a doctor <ArrowRight size={18}/></button></div>
          <div className="hero-art" aria-hidden="true"><div className="hero-orb"><HeartPulse/></div><div className="floating one"><ShieldCheck size={19}/> Thoughtful care</div><div className="floating two"><CalendarDays size={19}/> Easy scheduling</div></div>
        </section>
        <h2 className="section-title">How can we help you today?</h2>
        <div className="quick-grid">
          <button className="tile" onClick={()=>navigate("doctors")}><span className="tile-icon"><Stethoscope/></span><strong>Find a specialist</strong><span className="sub">Explore clinicians and their specialties.</span><ArrowRight size={18} color="#0a807c"/></button>
          <button className="tile" onClick={()=>navigate("appointments")}><span className="tile-icon"><CalendarDays/></span><strong>My appointments</strong><span className="sub">See your scheduled virtual visits.</span><ArrowRight size={18} color="#0a807c"/></button>
          <button className="tile" onClick={()=>navigate("account")}><span className="tile-icon"><ShieldCheck/></span><strong>My account</strong><span className="sub">Access your patient account securely.</span><ArrowRight size={18} color="#0a807c"/></button>
        </div>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:12}}><h2 className="section-title">Meet our clinicians</h2><button className="link" onClick={()=>navigate("doctors")}>View all <ArrowRight size={15}/></button></div>
        {loading ? <p className="loading" role="status">Loading clinicians…</p> : error ? <p className="error" role="alert">{error} <button className="link" onClick={()=>void getDoctors()}>Retry</button></p> : <DoctorGrid doctors={doctors.slice(0,3)} onSelect={chooseDoctor}/>}
      </>}
      {page==="doctors" && <>
        <p className="eyebrow">FIND THE RIGHT CARE</p><h1 className="title">Find your clinician</h1><p className="lead">Explore the directory and choose a convenient time for a virtual consultation.</p>
        <div className="searchline">
          <label className="searchbox"><Search size={19} color="#6b7d87"/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search by clinician name" aria-label="Search clinicians by name"/></label>
          <select className="select" value={specialty} onChange={e=>setSpecialty(e.target.value)} aria-label="Filter by specialty"><option value="">All specialties</option>{specialties.map(s=><option key={s} value={s}>{s}</option>)}</select>
        </div>
        {loading ? <p className="loading" role="status">Finding clinicians…</p> : error ? <div className="error" role="alert">{error}<div><button className="link" onClick={()=>void getDoctors()}>Try again</button></div></div> : <DoctorGrid doctors={doctors} onSelect={chooseDoctor}/>}
      </>}
      {(page==="doctor"||page==="booking") && doctor && <>
        <button className="back" onClick={()=>navigate(page==="booking"?"doctor":"doctors")}><ArrowLeft size={17}/> Back to {page==="booking"?"profile":"clinicians"}</button>
        <p className="eyebrow">{page==="booking"?"BOOK A VISIT":"CLINICIAN PROFILE"}</p><h1 className="title">{page==="booking"?"Choose an appointment time":fullName(doctor)}</h1>
        {page==="doctor"?<div className="profile-grid">
          <div className="card"><div className="avatar" style={{width:88,height:88}}><UserRound size={43}/></div><h2>{fullName(doctor)}</h2><p className="lead">{doctor.roles?.map(x=>x.specialty).join(" · ") || "Healthcare professional"}</p><p className="rating"><Star size={17} fill="currentColor"/> {doctor.average_rating ?? "New"} · {doctor.review_count??0} reviews</p><h3>About</h3><p className="lead">{doctor.bio || "Review available appointment times and find a visit that works for you."}</p></div>
          <aside className="card"><h2 style={{marginTop:0}}>Ready to connect?</h2><p className="lead">See available appointments and choose the time that fits your schedule.</p><div className="notice">Provider eligibility, licensing and service area must be verified before clinical use.</div><br/><button className="btn" onClick={()=>void viewSlots()}>View available times <ArrowRight size={17}/></button></aside>
        </div>:<div className="profile-grid">
          <section className="card"><h2 style={{marginTop:0}}>Available appointments</h2><p className="sub">Times are displayed in your device's timezone. Showing the next seven days.</p>
          {loading?<p className="loading" role="status">Loading availability…</p>:slots.length?<div className="slot-grid">{slots.map(s=><button key={s.start} className={`slot ${selectedSlot===s.start?"selected":""}`} onClick={()=>setSelectedSlot(s.start)} aria-pressed={selectedSlot===s.start}>{format(s.start)}</button>)}</div>:!error?<p className="empty">No available slots in the next seven days.</p>:null}</section>
          <aside className="card"><p className="eyebrow">APPOINTMENT SUMMARY</p><h2>{fullName(doctor)}</h2><p className="sub">{doctor.roles?.[0]?.specialty || "Virtual consultation"}</p><div className="list-item"><span>Visit type</span><strong><Video size={16} style={{verticalAlign:"middle"}}/> Video</strong></div><div className="list-item"><span>When</span><strong>{selectedSlot?format(selectedSlot):"Select a time"}</strong></div><br/><button className="btn" onClick={()=>void book()} disabled={!selectedSlot||busy}>{busy?"Confirming…":signedIn?"Confirm appointment":"Sign in to book"} <ArrowRight size={17}/></button><p className="sub">This prototype must not be used for sensitive healthcare information.</p></aside>
        </div>}
        {error&&<p className="error" role="alert">{error}</p>}
      </>}
      {page==="appointments"&&<>
        <p className="eyebrow">YOUR CARE JOURNEY</p><h1 className="title">My appointments</h1><p className="lead">Keep track of your scheduled virtual consultations.</p>
        {success&&<div className="notice" role="status"><CheckCircle2 size={17} style={{verticalAlign:"middle"}}/> {success}</div>}
        {!signedIn?<section className="card" style={{maxWidth:540,marginTop:24}}><LockKeyhole color="#0a807c" size={32}/><h2>Sign in to see your visits</h2><p className="lead">Your appointment details are available only after authentication.</p><button className="btn" onClick={()=>setAuthOpen(true)}>Sign in <ArrowRight size={17}/></button></section>:<section className="card" style={{marginTop:24}}>{loading?<p className="loading">Loading appointments…</p>:visits.length?visits.map(v=><div className="list-item" key={v.id}><div><strong>{format(v.scheduled_start)}</strong><p className="sub"><Video size={15} style={{verticalAlign:"middle"}}/> Virtual consultation · {v.id.slice(0,8)}</p></div><span className="badge">{v.status.replaceAll("_"," ")}</span></div>):!error?<div className="empty"><CalendarDays size={35} style={{margin:"0 auto 10px"}}/><p>No appointments yet.</p><button className="btn secondary" onClick={()=>navigate("doctors")}>Find a clinician</button></div>:null}{error&&<p className="error" role="alert">{error}</p>}</section>}
      </>}
      {page==="account"&&<>
        <p className="eyebrow">YOUR ACCOUNT</p><h1 className="title">Account & preferences</h1><div className="card" style={{maxWidth:610,marginTop:20}}><div className="avatar"><UserRound size={30}/></div><h2>{signedIn?"Patient account":"Welcome to CareConnect"}</h2><p className="lead">{signedIn?"You are signed in. Full profile features are under development.":"Sign in or create a patient account to manage your appointments."}</p><button className="btn" onClick={()=>signedIn?void signOut():setAuthOpen(true)}>{signedIn?<><LogOut size={17}/> Sign out</>:<><LockKeyhole size={17}/> Sign in or register</>}</button></div>
      </>}
    </main>
    <footer className="footer"><div className="shell"><HeartPulse size={16} style={{verticalAlign:"middle"}}/> CareConnect · Development preview · For demonstration only; not for medical emergencies or real patient information.</div></footer>
    {authOpen&&<div className="modal-bg" onMouseDown={e=>{if(e.target===e.currentTarget){setAuthOpen(false);setError("");}}}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="auth-heading"><div className="modal-top"><span className="eyebrow">PATIENT ACCESS</span><button className="close" onClick={()=>{setAuthOpen(false);setError("");}} aria-label="Close"><X/></button></div><h2 id="auth-heading" className="title">{register?"Create your account":"Welcome back"}</h2><p className="lead">{register?"Create a patient account to get started.":"Sign in to manage your healthcare appointments."}</p><form className="form" onSubmit={e=>{e.preventDefault();void auth();}}><label>Email address<input className="field" type="email" autoComplete="email" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com"/></label><label>Password<input className="field" type="password" autoComplete={register?"new-password":"current-password"} required minLength={register?12:1} value={password} onChange={e=>setPassword(e.target.value)} placeholder={register?"At least 12 characters":"Enter your password"}/></label>{error&&<p className="error" role="alert">{error}</p>}<button type="submit" className="btn" disabled={busy}>{busy?"Please wait…":register?"Create account":"Sign in"} <ArrowRight size={17}/></button></form><p style={{textAlign:"center"}}><button className="link" onClick={()=>{setRegister(!register);setError("");}}>{register?"Already have an account? Sign in":"New here? Create an account"}</button></p></section></div>}
  </>;
}
function DoctorGrid({doctors,onSelect}:{doctors:Clinician[];onSelect:(doctor:Clinician)=>void}) {
  if(!doctors.length) return <div className="card empty">No clinicians found. Try another search or specialty.</div>;
  return <div className="doctor-grid">{doctors.map(d=><button key={d.id} className="doctor-card card" onClick={()=>onSelect(d)} aria-label={`View profile for ${fullName(d)}`}><div className="avatar"><UserRound size={33}/></div><h3>{fullName(d)}</h3><span className="sub">{d.roles?.map(r=>r.specialty).join(" · ") || "Healthcare professional"}</span><span className="rating"><Star size={15} fill="currentColor"/> {d.average_rating??"New"} <span className="sub">({d.review_count??0} reviews)</span></span><span className="doctor-foot"><span className="sub">View profile</span><ChevronRight color="#0a807c" size={19}/></span></button>)}</div>;
}
