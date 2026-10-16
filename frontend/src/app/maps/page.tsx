'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
type Facility={id:string;name:string;address:string;latitude:number|null;longitude:number|null};
export default function Maps(){const [facilities,setFacilities]=useState<Facility[]>([]),[error,setError]=useState('');const key=process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
useEffect(()=>{fetch('/api/facilities').then(async r=>{const d=await r.json();if(!r.ok)throw new Error(d.error);setFacilities(d.facilities)}).catch(e=>setError(String(e)))},[]);
const located=facilities.filter(f=>f.latitude!==null&&f.longitude!==null);
return <main className="admin-workspace"><Link href="/">← Dashboard</Link><h1>Facility maps</h1><p>Only facilities with verified coordinates are mapped. No locations are guessed.</p>{error&&<p role="alert">{error}</p>}{!key&&<p className="auth-error">Configure NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to enable embedded Google Maps.</p>}<div className="admin-card"><h2>Mapped facilities ({located.length})</h2>{located.map(f=><div className="admin-user" key={f.id}><strong>{f.name}</strong><span>{f.address}</span><a target="_blank" rel="noopener noreferrer" href={'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(f.latitude+','+f.longitude)}>Open directions ↗</a></div>)}{!located.length&&<p>No verified facility coordinates yet.</p>}</div></main>}
