import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StatusBar, StyleSheet, Text, TextInput, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { api, Appointment, Clinician, session } from "./src/api";

const C = { background: "#F7F9FB", white: "#FFFFFF", ink: "#152B3D", muted: "#647987", teal: "#087E83", pale: "#E5F4F2", border: "#E4EBEF", amber: "#FFF3E2", danger: "#B64040" };
type Page = "home" | "search" | "appointments" | "profile" | "clinician" | "booking";
type AuthMode = "login" | "register";
const today = () => new Date().toISOString().slice(0, 10);
const inDays = (n: number) => new Date(Date.now() + n * 86400000).toISOString().slice(0, 10);
const formatTime = (iso: string) => new Date(iso).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

function Icon({name, size = 21, color = C.ink}: {name: React.ComponentProps<typeof Ionicons>["name"]; size?: number; color?: string}) {
  return <Ionicons name={name} size={size} color={color}/>;
}
function Button({title, onPress, secondary = false, disabled = false}: {title: string; onPress: () => void; secondary?: boolean; disabled?: boolean}) {
  return <Pressable accessibilityRole="button" accessibilityState={{disabled}} disabled={disabled} onPress={onPress} style={[styles.button, secondary && styles.secondary, disabled && {opacity: .5}]}>
    <Text style={[styles.buttonText, secondary && {color: C.teal}]}>{title}</Text>
  </Pressable>;
}
function ClinicianCard({doctor, onPress}: {doctor: Clinician; onPress: () => void}) {
  return <Pressable accessibilityRole="button" accessibilityLabel={`View Dr. ${doctor.first_name} ${doctor.last_name}`} onPress={onPress} style={styles.doctor}>
    <View style={styles.avatar}><Icon name="person" color={C.teal} size={27}/></View>
    <View style={{flex: 1, gap: 5}}>
      <Text style={styles.doctorName}>Dr. {doctor.first_name} {doctor.last_name}</Text>
      <Text style={styles.subtle}>{doctor.roles?.map(x => x.specialty).join(" · ") || "Healthcare professional"}</Text>
      <View style={styles.row}><Icon name="star" color="#D89F37" size={14}/><Text style={styles.small}>{doctor.average_rating ?? "New"}  ·  {doctor.review_count ?? 0} reviews</Text></View>
    </View>
    <Icon name="chevron-forward" size={18} color={C.muted}/>
  </Pressable>;
}
function Main() {
  const [page, setPage] = useState<Page>("home");
  const [doctors, setDoctors] = useState<Clinician[]>([]);
  const [specialties, setSpecialties] = useState<string[]>([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Clinician | null>(null);
  const [availability, setAvailability] = useState<Array<{start: string; is_available: boolean}>>([]);
  const [slot, setSlot] = useState("");
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [showAuth, setShowAuth] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { session.read().then(setToken).catch(() => setToken(null)); }, []);
  const loadDoctors = useCallback(async () => {
    setLoading(true); setError("");
    try { const data = await api.clinicians(search, selectedSpecialty); setDoctors(data.items); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load doctors."); }
    finally { setLoading(false); }
  }, [search, selectedSpecialty]);
  useEffect(() => {
    if (page === "home" || page === "search") void loadDoctors();
  }, [page, loadDoctors]);
  useEffect(() => { api.specialties().then(s => setSpecialties(s.map(x => x.name))).catch(() => {}); }, []);
  const loadAppointments = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError("");
    try { setAppointments((await api.appointments()).items); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load appointments."); }
    finally { setLoading(false); }
  }, [token]);
  useEffect(() => { if (page === "appointments") void loadAppointments(); }, [page, loadAppointments]);
  async function openDoctor(doctor: Clinician) {
    setSelected(doctor); setSlot(""); setAvailability([]); setPage("clinician"); setError("");
    try { const detail = await api.clinician(doctor.id); setSelected(detail); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load doctor details."); }
  }
  async function openBooking() {
    if (!selected) return;
    setPage("booking"); setLoading(true); setError("");
    try {
      const result = await api.availability(selected.id, today(), inDays(7));
      setAvailability(Object.values(result.availability).flat().filter(s => s.is_available && new Date(s.start).getTime() > Date.now()));
    } catch (e) { setError(e instanceof Error ? e.message : "Could not retrieve available times."); }
    finally { setLoading(false); }
  }
  async function authenticate() {
    if (!email.trim() || !password) { setError("Enter your email and password."); return; }
    if (authMode === "register" && password.length < 12) { setError("Use at least 12 characters for your password."); return; }
    setBusy(true); setError("");
    try {
      const result = authMode === "login" ? await api.login(email.trim(), password) : await api.register(email.trim(), password);
      if (result.role !== "patient") throw new Error("This app supports patient accounts only.");
      await session.save(result.tokens.access_token); setToken(result.tokens.access_token); setShowAuth(false); setPassword("");
      if (page === "appointments") void loadAppointments();
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to sign in."); }
    finally { setBusy(false); }
  }
  async function book() {
    if (!selected || !slot) return;
    if (!token) { setShowAuth(true); setError(""); return; }
    setBusy(true); setError("");
    try {
      const hold = await api.hold(selected.id, slot);
      await api.confirm(hold.hold_id);
      setPage("appointments"); setSlot(""); Alert.alert("Booked", "Your appointment has been confirmed.");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to book the appointment. Please try another time."); }
    finally { setBusy(false); }
  }
  async function signOut() {
    try { await api.logout(); } catch { /* Clear local session even when offline. */ }
    await session.clear(); setToken(null); setAppointments([]); setPage("home");
  }
  const heading = page === "home" ? "Good to see you" : ({search: "Find your doctor", appointments: "My appointments", profile: "Your account", clinician: "Doctor profile", booking: "Choose a time"} as const)[page];
  return <SafeAreaView style={styles.safe}>
    <StatusBar barStyle="dark-content" backgroundColor={C.background}/>
    <View style={styles.top}>
      <View style={styles.row}><View style={styles.brandIcon}><Icon name="medical" color={C.white} size={19}/></View><Text style={styles.brand}>care<Text style={{color: C.teal}}>connect</Text></Text></View>
      <Pressable accessibilityRole="button" accessibilityLabel="Open profile" onPress={() => {setError("");setPage("profile");}} style={styles.profileButton}><Icon name="person-outline" color={C.teal}/></Pressable>
    </View>
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      {(page === "clinician" || page === "booking") && <Pressable onPress={() => {setError("");setPage(page === "booking" ? "clinician" : "search");}} style={styles.back}><Icon name="arrow-back" size={18} color={C.teal}/><Text style={{color: C.teal, fontWeight: "600"}}>Back</Text></Pressable>}
      <Text style={styles.eyebrow}>{page === "home" ? "YOUR HEALTH, MADE SIMPLE" : "CARECONNECT"}</Text>
      <Text style={styles.heading}>{heading}</Text>
      {page === "home" && <>
        <View style={styles.hero}><View style={styles.heroLabel}><Icon name="heart" color={C.teal} size={14}/><Text style={{color: C.teal, fontWeight: "700", fontSize: 12}}>CARE THAT FITS YOUR LIFE</Text></View>
          <Text style={styles.heroTitle}>Better care, just a tap away.</Text>
          <Text style={styles.heroDesc}>Connect with healthcare professionals and manage your appointments in one place.</Text>
          <Button title="Find a doctor   →" onPress={() => setPage("search")}/>
        </View>
        <Text style={styles.sectionHeading}>What would you like to do?</Text>
        <View style={styles.actionRow}>
          <Pressable onPress={() => setPage("search")} style={styles.action}><View style={styles.actionIcon}><Icon name="search" color={C.teal}/></View><Text style={styles.actionText}>Find care</Text><Text style={styles.small}>Browse specialists</Text></Pressable>
          <Pressable onPress={() => setPage("appointments")} style={styles.action}><View style={styles.actionIcon}><Icon name="calendar-outline" color={C.teal}/></View><Text style={styles.actionText}>My visits</Text><Text style={styles.small}>View appointments</Text></Pressable>
        </View>
        <Text style={styles.sectionHeading}>Meet our care team</Text>
      </>}
      {(page === "home" || page === "search") && <>
        {page === "search" && <>
          <Text style={styles.intro}>Find a clinician who's right for you.</Text>
          <View style={styles.searchBar}><Icon name="search-outline" color={C.muted}/><TextInput placeholder="Search by name or specialty" placeholderTextColor={C.muted} value={search} onChangeText={setSearch} autoCapitalize="none" style={{flex:1,color:C.ink,fontSize:15}} accessibilityLabel="Search clinicians"/></View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{gap:8,paddingVertical:8}}>
            {["All specialties", ...specialties].map((item, i) => <Pressable key={item} onPress={() => setSelectedSpecialty(i === 0 ? "" : item)} style={[styles.chip,(i===0 && !selectedSpecialty || item===selectedSpecialty) && styles.chipActive]}><Text style={{color: (i===0 && !selectedSpecialty || item===selectedSpecialty) ? C.white : C.ink, fontWeight:"600"}}>{item}</Text></Pressable>)}
          </ScrollView>
        </>}
        {loading && <ActivityIndicator color={C.teal} style={{marginTop:24}}/>}
        {error ? <View style={styles.notice}><Text style={{color:C.danger}}>{error}</Text><Button title="Try again" secondary onPress={() => void loadDoctors()}/></View> : null}
        {!loading && !error && !doctors.length && <Text style={styles.empty}>No clinicians found. Try another search or specialty.</Text>}
        {!loading && doctors.map(d => <ClinicianCard key={d.id} doctor={d} onPress={() => void openDoctor(d)}/>)}
      </>}
      {page === "clinician" && selected && <>
        <View style={styles.card}><View style={[styles.avatar,{width:72,height:72,borderRadius:22,marginBottom:14}]}><Icon name="person" size={40} color={C.teal}/></View>
          <Text style={styles.doctorName}>Dr. {selected.first_name} {selected.last_name}</Text>
          <Text style={styles.subtle}>{selected.roles?.map(r=>r.specialty).join(", ") || "Healthcare professional"}</Text>
          <View style={[styles.row,{marginVertical:12}]}><Icon name="star" color="#D89F37"/><Text style={styles.small}>{selected.average_rating ?? "New"} · {selected.review_count ?? 0} reviews</Text></View>
          <Text style={styles.intro}>{selected.bio || "Find a convenient time to meet with this clinician."}</Text>
          <Text style={styles.small}>Availability and service eligibility are subject to confirmation.</Text>
        </View>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Button title="View available times" onPress={() => void openBooking()}/>
      </>}
      {page === "booking" && selected && <>
        <Text style={styles.intro}>Select an available video consultation with Dr. {selected.first_name} {selected.last_name}. Times are shown in your device's timezone.</Text>
        {loading && <ActivityIndicator color={C.teal}/>}
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {!loading && !error && !availability.length && <Text style={styles.empty}>No available times in the next seven days.</Text>}
        {availability.map(s => <Pressable key={s.start} onPress={() => setSlot(s.start)} style={[styles.slot,slot===s.start && styles.selectedSlot]}><Icon name="time-outline" color={C.teal}/><Text style={{color:C.ink,fontWeight:"600",flex:1}}>{formatTime(s.start)}</Text><Icon name={slot===s.start ? "radio-button-on" : "radio-button-off"} color={C.teal}/></Pressable>)}
        <Button title={busy ? "Booking…" : !token ? "Sign in to book" : "Confirm appointment"} disabled={!slot || busy} onPress={() => void book()}/>
        <Text style={styles.small}>This platform is a development prototype. Do not enter sensitive health information.</Text>
      </>}
      {page === "appointments" && <>
        {!token ? <View style={styles.card}><Icon name="lock-closed-outline" color={C.teal} size={34}/><Text style={styles.sectionHeading}>Sign in to view your visits</Text><Text style={styles.intro}>Your appointments are private and linked to your account.</Text><Button title="Sign in" onPress={() => setShowAuth(true)}/></View> : <>
          {loading && <ActivityIndicator color={C.teal}/>}
          {error && <Text style={styles.error}>{error}</Text>}
          {!loading && !appointments.length && <View style={styles.card}><Text style={styles.empty}>No appointments yet.</Text><Button title="Browse doctors" secondary onPress={() => setPage("search")}/></View>}
          {appointments.map(a=><View style={styles.card} key={a.id}><View style={styles.row}><Icon name="calendar-outline" color={C.teal}/><Text style={styles.doctorName}>{formatTime(a.scheduled_start)}</Text></View><Text style={styles.subtle}>Video consultation · {a.status.replaceAll("_"," ")}</Text><Text style={styles.small}>Appointment ID: {a.id.slice(0,8)}</Text></View>)}
        </>}
      </>}
      {page === "profile" && <View style={styles.card}><View style={[styles.avatar,{marginBottom:12}]}><Icon name="person-outline" color={C.teal}/></View><Text style={styles.sectionHeading}>{token ? "Patient account" : "Welcome to CareConnect"}</Text><Text style={styles.intro}>{token ? "Your session is active." : "Sign in to manage appointments and your account."}</Text><Button title={token ? "Sign out" : "Sign in or create an account"} onPress={() => token ? void signOut() : setShowAuth(true)}/></View>}
    </ScrollView>
    {showAuth ? <View style={styles.overlay}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.modal}>
      <Pressable accessibilityRole="button" accessibilityLabel="Close sign in" style={{alignSelf:"flex-end"}} onPress={() => {setShowAuth(false);setError("");}}><Icon name="close" size={25}/></Pressable>
      <View style={styles.brandIcon}><Icon name="medical" color={C.white}/></View>
      <Text style={styles.heading}>{authMode==="login" ? "Welcome back" : "Create your account"}</Text>
      <Text style={styles.intro}>Use your CareConnect patient account.</Text>
      <Text style={styles.fieldLabel}>Email address</Text><TextInput style={styles.input} placeholder="you@example.com" autoCapitalize="none" keyboardType="email-address" autoComplete="email" value={email} onChangeText={setEmail}/>
      <Text style={styles.fieldLabel}>Password</Text><TextInput style={styles.input} placeholder="Your password" secureTextEntry autoComplete={authMode==="login"?"current-password":"new-password"} value={password} onChangeText={setPassword}/>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Button title={busy ? "Please wait…" : authMode==="login" ? "Sign in" : "Create account"} disabled={busy} onPress={() => void authenticate()}/>
      <Pressable onPress={() => {setError("");setAuthMode(authMode==="login"?"register":"login");}} style={{padding:16,alignItems:"center"}}><Text style={{color:C.teal,fontWeight:"600"}}>{authMode==="login"?"New here? Create an account":"Already registered? Sign in"}</Text></Pressable>
    </ScrollView></View> : null}
    <View style={styles.tabs}>
      {([{page:"home",icon:"home-outline",label:"Home"},{page:"search",icon:"search-outline",label:"Find care"},{page:"appointments",icon:"calendar-outline",label:"My visits"},{page:"profile",icon:"person-outline",label:"Account"}] as const).map(tab=><Pressable accessibilityRole="tab" accessibilityState={{selected:page===tab.page}} key={tab.page} style={styles.tab} onPress={()=>{setError("");setPage(tab.page);}}>
        <Icon name={tab.icon} color={page===tab.page?C.teal:C.muted}/><Text style={[styles.tabLabel,page===tab.page && {color:C.teal,fontWeight:"700"}]}>{tab.label}</Text></Pressable>)}
    </View>
  </SafeAreaView>;
}
export default function App(){return <SafeAreaProvider><Main/></SafeAreaProvider>;}
const styles=StyleSheet.create({
 safe:{flex:1,backgroundColor:C.background},top:{paddingHorizontal:22,paddingVertical:13,flexDirection:"row",justifyContent:"space-between",alignItems:"center",borderBottomWidth:1,borderColor:C.border,backgroundColor:C.white},row:{flexDirection:"row",alignItems:"center",gap:7},brandIcon:{backgroundColor:C.teal,width:34,height:34,borderRadius:11,justifyContent:"center",alignItems:"center"},brand:{fontSize:21,fontWeight:"800",letterSpacing:-.7,color:C.ink},profileButton:{padding:9,backgroundColor:C.pale,borderRadius:13},content:{padding:22,paddingBottom:42,gap:14},eyebrow:{fontSize:10,fontWeight:"800",letterSpacing:2,color:C.teal},heading:{fontSize:30,lineHeight:37,fontWeight:"800",letterSpacing:-1,color:C.ink},hero:{backgroundColor:C.pale,padding:23,borderRadius:24,gap:14,marginTop:5},heroLabel:{flexDirection:"row",alignItems:"center",gap:7},heroTitle:{fontSize:29,fontWeight:"800",lineHeight:35,color:C.ink,letterSpacing:-.8,maxWidth:280},heroDesc:{fontSize:14,lineHeight:22,color:C.muted},button:{backgroundColor:C.teal,paddingVertical:15,borderRadius:13,alignItems:"center",justifyContent:"center",marginTop:5,minHeight:50},buttonText:{color:C.white,fontSize:14,fontWeight:"800"},secondary:{backgroundColor:C.pale},sectionHeading:{fontSize:18,fontWeight:"800",color:C.ink,marginTop:6},actionRow:{flexDirection:"row",gap:12},action:{flex:1,backgroundColor:C.white,borderWidth:1,borderColor:C.border,borderRadius:17,padding:17,gap:7},actionIcon:{width:42,height:42,borderRadius:13,backgroundColor:C.pale,alignItems:"center",justifyContent:"center"},actionText:{fontWeight:"800",color:C.ink,fontSize:15},small:{fontSize:12,color:C.muted},doctor:{flexDirection:"row",gap:12,alignItems:"center",padding:14,backgroundColor:C.white,borderRadius:17,borderWidth:1,borderColor:C.border},avatar:{height:56,width:56,borderRadius:17,backgroundColor:C.pale,justifyContent:"center",alignItems:"center"},doctorName:{fontSize:16,fontWeight:"800",color:C.ink},subtle:{fontSize:13,color:C.muted,lineHeight:20},intro:{fontSize:14,color:C.muted,lineHeight:22},searchBar:{flexDirection:"row",alignItems:"center",gap:9,padding:14,backgroundColor:C.white,borderRadius:14,borderWidth:1,borderColor:C.border,marginTop:5},chip:{paddingVertical:10,paddingHorizontal:14,backgroundColor:C.white,borderRadius:22,borderWidth:1,borderColor:C.border},chipActive:{backgroundColor:C.teal,borderColor:C.teal},card:{backgroundColor:C.white,borderRadius:20,borderWidth:1,borderColor:C.border,padding:20,gap:12},slot:{backgroundColor:C.white,borderRadius:14,borderWidth:1,borderColor:C.border,padding:16,flexDirection:"row",gap:12,alignItems:"center"},selectedSlot:{borderWidth:2,borderColor:C.teal,backgroundColor:C.pale},back:{flexDirection:"row",alignItems:"center",gap:7,marginBottom:4},error:{color:C.danger,fontSize:13,lineHeight:20},notice:{padding:12,gap:8,backgroundColor:C.white,borderRadius:12},empty:{paddingVertical:20,textAlign:"center",fontSize:14,color:C.muted},tabs:{flexDirection:"row",backgroundColor:C.white,borderTopWidth:1,borderColor:C.border,paddingVertical:8,paddingHorizontal:7},tab:{flex:1,alignItems:"center",gap:4,paddingVertical:6},tabLabel:{fontSize:11,color:C.muted},overlay:{position:"absolute",top:0,bottom:0,left:0,right:0,backgroundColor:C.background,zIndex:9},modal:{padding:28,gap:14,paddingTop:45},fieldLabel:{fontSize:13,fontWeight:"700",color:C.ink,marginTop:8},input:{borderWidth:1,borderColor:C.border,backgroundColor:C.white,borderRadius:12,paddingHorizontal:15,paddingVertical:14,fontSize:15,color:C.ink},
});
