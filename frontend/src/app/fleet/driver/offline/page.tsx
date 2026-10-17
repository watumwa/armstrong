'use client';
import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';

type Stop={id:string;facility_name:string;status:string};
type Trip={id:string;registration:string;status:string;stops:Stop[]};
type Event={client_event_id:string;event_type:'stop.verify';trip_stop_id:string;payload:{latitude:number;longitude:number;accuracy_m:number;qr_token:string;notes:string};created_at:string};
const KEY='armstrong:fleet:offline-stop-events:v1';
function readQueue():Event[]{try{const x=JSON.parse(localStorage.getItem(KEY)||'[]');return Array.isArray(x)?x:[]}catch{return []}}
function saveQueue(items:Event[]){localStorage.setItem(KEY,JSON.stringify(items))}
export default function OfflineCollections(){
 const [trips,setTrips]=useState<Trip[]>([]),[trip,setTrip]=useState(''),[stop,setStop]=useState(''),[token,setToken]=useState(''),[notes,setNotes]=useState(''),[queue,setQueue]=useState<Event[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{setQueue(readQueue());fetch('/api/fleet/trips').then(r=>r.json()).then(d=>setTrips((d.trips||[]).filter((t:Trip)=>t.status==='active'))).catch(()=>setMessage('Trips unavailable. Open this page online before going offline.'))},[]);
 const sync=useCallback(async()=>{
  const items=readQueue();if(!items.length)return;
  setBusy(true);
  try{
   const r=await fetch('/api/fleet/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({events:items.slice(0,20)})});
   if(!r.ok)throw Error('Sync request failed: '+r.status);
   const d=await r.json();
   const accepted=new Set<string>((d.results||[]).filter((x:{status:string})=>x.status==='accepted').map((x:{client_event_id:string})=>x.client_event_id));
   const remaining=readQueue().filter(e=>!accepted.has(e.client_event_id));
   saveQueue(remaining);setQueue(remaining);
   const rejected=(d.results||[]).filter((x:{status:string})=>x.status==='rejected');
   setMessage(accepted.size+' synced. '+rejected.length+' need review. '+remaining.length+' still pending.');
  }catch(e){setMessage('Sync unavailable; saved events retained. '+String(e))}finally{setBusy(false)}
 },[]);
 useEffect(()=>{const onOnline=()=>{void sync()};window.addEventListener('online',onOnline);return()=>window.removeEventListener('online',onOnline)},[sync]);
 function capture(){
  if(!stop||!token.trim()){setMessage('Choose a stop and scan or paste its facility QR token.');return}
  if(!navigator.geolocation){setMessage('GPS unavailable.');return}
  setMessage('Getting current GPS position...');
  navigator.geolocation.getCurrentPosition(p=>{
   const event:Event={client_event_id:crypto.randomUUID(),event_type:'stop.verify',trip_stop_id:stop,
    payload:{latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy_m:p.coords.accuracy,qr_token:token.trim(),notes},created_at:new Date().toISOString()};
   const current=readQueue();
   if(current.length>=100){setMessage('Queue full (100 events). Sync existing events first.');return}
   const next=[...current,event];
   try{saveQueue(next);setQueue(next);setMessage('Stop proof saved on this device. Sync when online.');setToken('');setNotes('')}
   catch{setMessage('Device storage unavailable. Proof was NOT saved.')}
  },e=>setMessage('GPS capture failed: '+e.message),{enableHighAccuracy:true,maximumAge:0,timeout:20000});
 }
 const selected=trips.find(t=>t.id===trip);
 return <main style={{maxWidth:720,margin:'auto',padding:24}}><Link href="/fleet/driver">← Driver</Link><h1>Offline collection proof</h1><p>Capture a facility QR token and live GPS position while on site. Events are saved in this browser and can be synchronized later. Keep this browser's storage intact until all events are accepted.</p>
 <label>Active trip<select value={trip} onChange={e=>{setTrip(e.target.value);setStop('')}} style={{display:'block',padding:12,width:'100%',marginBottom:16}}><option value="">Select trip</option>{trips.map(t=><option key={t.id} value={t.id}>{t.registration}</option>)}</select></label>
 <label>Facility stop<select value={stop} onChange={e=>setStop(e.target.value)} style={{display:'block',padding:12,width:'100%',marginBottom:16}}><option value="">Select stop</option>{selected?.stops.filter(s=>s.status!=='completed').map(s=><option key={s.id} value={s.id}>{s.facility_name}</option>)}</select></label>
 <label>Signed facility QR token<input value={token} onChange={e=>setToken(e.target.value)} placeholder="Paste scanned token" style={{display:'block',padding:12,width:'100%',marginBottom:16}}/></label>
 <label>Notes<textarea value={notes} onChange={e=>setNotes(e.target.value)} maxLength={1000} style={{display:'block',padding:12,width:'100%',marginBottom:16}}/></label>
 <div style={{display:'flex',gap:12,flexWrap:'wrap'}}><button onClick={capture} disabled={!stop} style={{padding:14}}>Save proof offline</button><button onClick={()=>void sync()} disabled={busy||!queue.length} style={{padding:14}}>{busy?'Syncing...':'Sync saved events'}</button></div>
 <p role="status">{message}</p><h2>Pending sync: {queue.length}</h2>{queue.map(e=><p key={e.client_event_id}>{e.created_at} · {e.trip_stop_id.slice(0,8)} · pending</p>)}
 <p>Important: browser storage is not guaranteed durable if app data is cleared or the device is lost. GPS is captured at the time of saving; the server validates location and trip state when syncing. Offline GPS tracking is not enabled.</p></main>
}
