'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
type Alert={id:string;severity:string;category:string;message:string;created_at:string;resolved_at:string|null};
export default function FleetAlerts(){
 const [alerts,setAlerts]=useState<Alert[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 async function load(){try{const r=await fetch('/api/fleet/alerts?unresolved=true');const d=await r.json();if(!r.ok)throw Error(d.error||'Access denied');setAlerts(d.alerts||[])}catch(e){setMessage(String(e))}}
 useEffect(()=>{void load()},[]);
 async function action(url:string){setBusy(true);try{const r=await fetch(url,{method:'POST'});const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');setMessage('Updated successfully.');await load()}catch(e){setMessage(String(e))}finally{setBusy(false)}}
 return <main style={{maxWidth:900,margin:'auto',padding:24}}><Link href="/fleet">← Fleet</Link><h1>Fleet alerts</h1><p>Review overdue departures and missing GPS updates. Scanning is manual; no SMS messages are sent.</p>
 <button disabled={busy} onClick={()=>void action('/api/fleet/alerts/scan')} style={{padding:12}}>Scan for operational alerts</button><p role="status">{message}</p>
 {alerts.length===0?<p>No unresolved alerts currently loaded.</p>:alerts.map(a=><article key={a.id} style={{border:'1px solid #ddd',borderRadius:12,padding:16,margin:'12px 0'}}><strong>{a.category.replaceAll('_',' ')} · {a.severity}</strong><p>{a.message}</p><small>{new Date(a.created_at).toLocaleString()}</small><p><button disabled={busy} onClick={()=>void action('/api/fleet/alerts/'+a.id+'/resolve')}>Mark resolved</button></p></article>)}
 </main>
}
