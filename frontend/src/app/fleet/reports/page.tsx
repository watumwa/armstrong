'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
type Summary={vehicles:number;available_vehicles:number;verified_stops:number;gps_reports:number;trips_by_status:Record<string,number>;stops_by_status:Record<string,number>};
export default function FleetReports(){
 const [data,setData]=useState<Summary|null>(null),[error,setError]=useState('');
 useEffect(()=>{fetch('/api/fleet/reports/summary').then(async r=>{const d=await r.json();if(!r.ok)throw Error(d.error||'Access denied');setData(d)}).catch(e=>setError(String(e)))},[]);
 return <main style={{maxWidth:960,margin:'auto',padding:24}}><Link href="/fleet">← Fleet</Link><h1>Fleet performance</h1><p>Cumulative operational totals. Access is restricted to Administrators and Supervisors.</p>{error&&<p role="alert">{error}</p>}{!data&&!error&&<p>Loading reports...</p>}{data&&<><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(170px,1fr))',gap:14}}>{[['Registered vehicles',data.vehicles],['Available vehicles',data.available_vehicles],['Verified facility stops',data.verified_stops],['GPS reports',data.gps_reports]].map(([label,value])=><section key={String(label)} style={{padding:20,border:'1px solid #e1e6ed',borderRadius:12}}><p>{label}</p><strong style={{fontSize:32}}>{value}</strong></section>)}</div><h2>Trips by status</h2>{Object.entries(data.trips_by_status).map(([status,count])=><p key={status}>{status}: {count}</p>)}<h2>Facility stops by status</h2>{Object.entries(data.stops_by_status).map(([status,count])=><p key={status}>{status}: {count}</p>)}</>}</main>
}
