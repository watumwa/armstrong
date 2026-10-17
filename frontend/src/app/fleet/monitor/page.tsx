'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
type Position={latitude:number;longitude:number;accuracy_m:number;captured_at:string;received_at:string};
type Truck={trip_id:string;registration:string;driver_name:string;last_location:Position|null;fresh:boolean};
export default function FleetMap(){
 const [vehicles,setVehicles]=useState<Truck[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 async function refresh(){try{const r=await fetch('/api/fleet/locations/latest');const d=await r.json();if(!r.ok)throw Error(d.error||'Unable to load locations');setVehicles(d.vehicles);setError('')}catch(e){setError(String(e))}finally{setLoading(false)}}
 useEffect(()=>{void refresh();const timer=setInterval(()=>void refresh(),30000);return()=>clearInterval(timer)},[]);
 return <main style={{maxWidth:1000,margin:'auto',padding:24}}><Link href="/fleet">← Fleet</Link><h1>Fleet location monitor</h1><p>Locations are reported by drivers during active trips. A location is marked recent only when received within 2 minutes. This is not continuous live tracking.</p>{error&&<p role="alert">{error}</p>}{loading&&<p>Loading vehicles...</p>}{vehicles.map(v=><section key={v.trip_id} style={{background:'white',padding:20,borderRadius:12,marginBottom:14,border:'1px solid #dce4ed'}}><h2>{v.registration}</h2><p>{v.driver_name} · {v.last_location?(v.fresh?'Recent update':'Last known location — stale'):'No location received'}</p>{v.last_location&&<><p>Recorded: {new Date(v.last_location.captured_at).toLocaleString()} · Accuracy ±{Math.round(v.last_location.accuracy_m)} m</p><a target="_blank" rel="noopener noreferrer" href={'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(v.last_location.latitude+','+v.last_location.longitude)}>View last reported position on map ↗</a></>}</section>)}{!loading&&!vehicles.length&&<p>No active trips are currently reporting.</p>}</main>
}
