'use client';
import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
type Trip={id:string;registration:string;status:string;driver_name:string};
export default function DriverTracking(){
 const [trips,setTrips]=useState<Trip[]>([]),[selected,setSelected]=useState(''),[running,setRunning]=useState(false),[message,setMessage]=useState('Tracking is off.'),[count,setCount]=useState(0);
 const watch=useRef<number|null>(null),last=useRef(0),inFlight=useRef(false);
 useEffect(()=>{fetch('/api/fleet/trips').then(r=>r.json()).then(d=>setTrips((d.trips||[]).filter((t:Trip)=>t.status==='active'))).catch(()=>setMessage('Could not load active trips.'));return ()=>{if(watch.current!==null)navigator.geolocation.clearWatch(watch.current)}},[]);
 function stop(){if(watch.current!==null){navigator.geolocation.clearWatch(watch.current);watch.current=null}setRunning(false);setMessage('Tracking stopped. No more locations will be sent.')}
 function start(){
  if(!selected){setMessage('Select an active trip.');return}
  if(!('geolocation' in navigator)){setMessage('This device does not support location tracking.');return}
  if(watch.current!==null)return;
  setMessage('Requesting location permission...');
  watch.current=navigator.geolocation.watchPosition(async position=>{
   const now=Date.now();if(now-last.current<30000||inFlight.current)return;
   inFlight.current=true;
   try{
    const r=await fetch('/api/fleet/trips/'+selected+'/location',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
     latitude:position.coords.latitude,longitude:position.coords.longitude,
     accuracy_m:position.coords.accuracy,captured_at:new Date(position.timestamp).toISOString(),
     client_event_id:crypto.randomUUID()})});
    const d=await r.json();if(!r.ok)throw Error(d.error||'GPS update failed');
    last.current=now;setCount(n=>n+1);setMessage('Last GPS update sent at '+new Date().toLocaleTimeString());
   }catch(e){setMessage('Location not sent: '+String(e))}finally{inFlight.current=false}
  },err=>{stop();setMessage('GPS unavailable: '+err.message)},{enableHighAccuracy:true,maximumAge:10000,timeout:20000});
  setRunning(true);
 }
 return <main style={{maxWidth:640,margin:'auto',padding:24}}><Link href="/fleet">← Fleet</Link><h1>Driver GPS tracking</h1><p><Link href="/fleet/driver/offline">Offline collection proof →</Link></p><p>Tracking is voluntary and only operates while this page is active and an assigned trip is running. It stops when you select Stop or leave the page. Browser tracking may pause when your phone locks.</p><label htmlFor="trip">Active assigned trip</label><select id="trip" disabled={running} style={{display:'block',padding:12,width:'100%',margin:'12px 0'}} value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Select trip</option>{trips.map(t=><option key={t.id} value={t.id}>{t.registration} — {t.driver_name}</option>)}</select><button onClick={running?stop:start} disabled={!running&&!selected} style={{padding:16,borderRadius:10,background:running?'#9b2525':'#167a57',color:'white',border:0}}>{running?'Stop tracking':'Start tracking'}</button><p role="status" style={{marginTop:20}}>{message}</p><p>GPS updates accepted in this session: {count}</p><p>No GPS locations are collected while tracking is off.</p></main>
}
