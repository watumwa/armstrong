'use client';

import {useEffect, useState} from 'react';
import Link from 'next/link';

type Me={user:{role:string}};
type Facility={id:string;name:string;phone:string;sms_opt_in:boolean};
type Reminder={id:string;kind:string;facility_name:string;recipient_phone:string;message:string;status:string;scheduled_for:string;sent_at:string|null;last_error:string|null};

const card={background:'#fff',border:'1px solid #dbe5ec',borderRadius:14,padding:20,marginBottom:18};

async function api<T>(path:string, method='GET', body?:unknown):Promise<T>{
 const response=await fetch(path,{method,headers:body===undefined?undefined:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await response.json();if(!response.ok)throw new Error(data.error||'Request failed');return data as T;
}

export default function RemindersPage(){
 const [role,setRole]=useState(''),[facilities,setFacilities]=useState<Facility[]>([]),[reminders,setReminders]=useState<Reminder[]>([]),[notice,setNotice]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const admin=role==='Administrator';
 async function load(){try{const [me,facilityData,reminderData]=await Promise.all([api<Me>('/api/auth/me'),api<{facilities:Facility[]}>('/api/facilities'),api<{reminders:Reminder[]}>('/api/reminders')]);setRole(me.user.role);setFacilities(facilityData.facilities);setReminders(reminderData.reminders)}catch(err){setError(err instanceof Error?err.message:'Unable to load reminders')}}
 useEffect(()=>{void load()},[]);
 async function setConsent(facility:Facility, sms_opt_in:boolean){setBusy(true);setError('');try{await api('/api/facilities/'+facility.id,'PATCH',{sms_opt_in});setNotice(sms_opt_in?'SMS consent recorded.':'SMS consent withdrawn.');await load()}catch(err){setError(err instanceof Error?err.message:'Could not update consent')}finally{setBusy(false)}}
 async function action(path:string){setBusy(true);setError('');try{const result=await api<{message?:string;queued?:Record<string,number>;sent?:number;failed?:number;not_configured?:boolean}>(path,'POST',{});const queued=result.queued?Object.values(result.queued).reduce((total,value)=>total+value,0):0;setNotice(result.not_configured?'Reminders are queued, but no SMS provider is configured.':result.queued?queued+' consented reminders queued.':(result.sent||0)+' sent; '+(result.failed||0)+' failed.');await load()}catch(err){setError(err instanceof Error?err.message:'Reminder action failed')}finally{setBusy(false)}}
 return <main style={{maxWidth:1080,margin:'auto',padding:'24px 18px',color:'#19364d'}}><Link href="/">← Dashboard</Link><h1>Client SMS reminders</h1><p>Upcoming collection and overdue-balance messages are queued only for clients whose SMS consent has been recorded. The outbox stores every attempt and provider result.</p>{error&&<p role="alert" style={{color:'#b42318'}}>{error}</p>}{notice&&<p role="status" style={{color:'#08734c'}}>{notice}</p>}
  {admin&&<section style={card}><h2>Reminder run</h2><p>Queue eligible reminders first, then dispatch them through the configured SMS provider.</p><div style={{display:'flex',gap:10,flexWrap:'wrap'}}><button disabled={busy} onClick={()=>void action('/api/reminders/queue')}>Queue consented reminders</button><button disabled={busy} onClick={()=>void action('/api/reminders/dispatch')}>Send queued reminders</button></div></section>}
  <section style={card}><h2>SMS consent by client</h2><p>Consent is required before a phone number is ever added to the reminder outbox.</p><div style={{display:'grid',gap:10}}>{facilities.map(facility=><article key={facility.id} style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',borderTop:'1px solid #e3ebef',paddingTop:10,flexWrap:'wrap'}}><div><strong>{facility.name}</strong><small style={{display:'block'}}>{facility.phone||'No phone number recorded'}</small></div><label><input disabled={!admin||busy||!facility.phone} type="checkbox" checked={facility.sms_opt_in} onChange={event=>void setConsent(facility,event.target.checked)}/> SMS consent recorded</label></article>)}{facilities.length===0&&<p>No clients available.</p>}</div></section>
  <section style={card}><h2>Reminder outbox</h2>{reminders.length===0?<p>No reminders have been queued.</p>:<div style={{display:'grid',gap:10}}>{reminders.map(reminder=><article key={reminder.id} style={{borderTop:'1px solid #e3ebef',paddingTop:11}}><strong>{reminder.kind.replace('_',' ')} · {reminder.facility_name}</strong><small style={{display:'block'}}>{reminder.recipient_phone} · {reminder.status} · {new Date(reminder.scheduled_for).toLocaleString()}</small><p style={{margin:'6px 0'}}>{reminder.message}</p>{reminder.last_error&&<small style={{color:'#b42318'}}>{reminder.last_error}</small>}</article>)}</div>}</section>
 </main>;
}
