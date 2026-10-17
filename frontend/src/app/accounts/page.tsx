'use client';

import {FormEvent, useEffect, useMemo, useState} from 'react';
import Link from 'next/link';

type Facility={id:string;name:string;phone:string;sms_opt_in:boolean};
type Invoice={id:string;facility_id:string;facility_name:string;invoice_number:string;due_date:string;status:string;subtotal:string;amount_paid:string;balance:string};
type Payment={id:string;reference:string;facility_id:string;facility_name:string;amount:string;method:string;status:string;paid_at:string;unallocated_amount:string};
type Summary={currency:string;invoices:number;invoiced:string;outstanding:string;overdue:string;confirmed_payments:string;pending_payments:string};
type Me={user:{role:string}};

const fieldStyle={display:'grid',gap:6,marginBottom:12};
const inputStyle={padding:10,border:'1px solid #cbd5df',borderRadius:8,width:'100%'};
const cardStyle={background:'#fff',border:'1px solid #dbe5ec',borderRadius:14,padding:20,marginBottom:18};
const money=(value:string)=>'UGX '+Number(value).toLocaleString('en-UG',{minimumFractionDigits:2,maximumFractionDigits:2});

async function request<T>(path:string, body?:unknown):Promise<T>{
 const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:body===undefined?undefined:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await response.json();
 if(!response.ok)throw new Error(data.error||'Request failed');
 return data as T;
}

export default function AccountsPage(){
 const [role,setRole]=useState(''),[facilities,setFacilities]=useState<Facility[]>([]),[invoices,setInvoices]=useState<Invoice[]>([]),[payments,setPayments]=useState<Payment[]>([]),[summary,setSummary]=useState<Summary|null>(null),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
 const [facilityId,setFacilityId]=useState(''),[dueDate,setDueDate]=useState(''),[description,setDescription]=useState('Monthly clinical waste service'),[quantity,setQuantity]=useState('1'),[unitPrice,setUnitPrice]=useState('');
 const [paymentFacilityId,setPaymentFacilityId]=useState(''),[amount,setAmount]=useState(''),[method,setMethod]=useState('Mobile Money');
 const [confirming,setConfirming]=useState<Payment|null>(null),[invoiceId,setInvoiceId]=useState(''),[allocation,setAllocation]=useState('');
 const managers=role==='Administrator'||role==='Revenue Officer';
 const canConfirm=role==='Administrator';
 const openForSelectedPayment=useMemo(()=>invoices.filter(invoice=>invoice.facility_id===confirming?.facility_id&&['issued','part_paid','overdue'].includes(invoice.status)&&Number(invoice.balance)>0),[confirming,invoices]);
 async function reload(){
  setError('');
  try{const [me,facilityResult,summaryResult,invoiceResult,paymentResult]=await Promise.all([
   request<Me>('/api/auth/me'),request<{facilities:Facility[]}>('/api/facilities'),request<Summary>('/api/accounts/summary'),request<{invoices:Invoice[]}>('/api/accounts/invoices'),request<{payments:Payment[]}>('/api/payments')
  ]);setRole(me.user.role);setFacilities(facilityResult.facilities);setSummary(summaryResult);setInvoices(invoiceResult.invoices);setPayments(paymentResult.payments)}catch(e){setError(e instanceof Error?e.message:'Unable to load accounts')}
 }
 useEffect(()=>{void reload()},[]);
 async function issueInvoice(event:FormEvent){event.preventDefault();setBusy(true);setError('');try{await request('/api/accounts/invoices',{facility_id:facilityId,due_date:dueDate,lines:[{description,quantity,unit_price:unitPrice}]});setNotice('Invoice issued and balance recorded.');setDescription('Monthly clinical waste service');setQuantity('1');setUnitPrice('');await reload()}catch(e){setError(e instanceof Error?e.message:'Could not issue invoice')}finally{setBusy(false)}}
 async function recordPayment(event:FormEvent){event.preventDefault();setBusy(true);setError('');try{await request('/api/payments',{facility_id:paymentFacilityId,amount,method});setNotice('Payment recorded as pending reconciliation.');setAmount('');await reload()}catch(e){setError(e instanceof Error?e.message:'Could not record payment')}finally{setBusy(false)}}
 async function confirmPayment(event:FormEvent){event.preventDefault();if(!confirming)return;setBusy(true);setError('');try{const allocations=invoiceId?[{invoice_id:invoiceId,amount:allocation}]:[];await request('/api/accounts/payments/'+confirming.id+'/confirm',{allocations});setNotice('Payment confirmed. You can now print its receipt.');setConfirming(null);setInvoiceId('');setAllocation('');await reload()}catch(e){setError(e instanceof Error?e.message:'Could not confirm payment')}finally{setBusy(false)}}
 return <main style={{maxWidth:1180,margin:'auto',padding:'24px 18px',color:'#19364d'}}>
  <Link href="/">← Dashboard</Link><h1>Accounts & reconciliation</h1><p>Issue invoices, record payments, reconcile payment allocations and print receipts. Confirmed balances are server-calculated.</p>
  {error&&<p role="alert" style={{color:'#b42318'}}>{error}</p>}{notice&&<p role="status" style={{color:'#08734c'}}>{notice}</p>}
  <section style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(165px,1fr))',gap:12,margin:'20px 0'}}>{summary&&[
   ['Outstanding',money(summary.outstanding)],['Overdue',money(summary.overdue)],['Confirmed payments',money(summary.confirmed_payments)],['Pending reconciliation',money(summary.pending_payments)]
  ].map(([label,value])=><article key={label} style={cardStyle}><small>{label}</small><strong style={{display:'block',fontSize:20,marginTop:8}}>{value}</strong></article>)}</section>
  {managers&&<section style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:18}}>
   <form onSubmit={issueInvoice} style={cardStyle}><h2>Issue invoice</h2><label style={fieldStyle}>Facility<select required value={facilityId} onChange={event=>setFacilityId(event.target.value)} style={inputStyle}><option value="">Select facility</option>{facilities.map(facility=><option key={facility.id} value={facility.id}>{facility.name}</option>)}</select></label><label style={fieldStyle}>Due date<input required type="date" min={new Date().toISOString().slice(0,10)} value={dueDate} onChange={event=>setDueDate(event.target.value)} style={inputStyle}/></label><label style={fieldStyle}>Description<input required value={description} onChange={event=>setDescription(event.target.value)} style={inputStyle}/></label><div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}><label style={fieldStyle}>Quantity<input required type="number" min="0.001" step="0.001" value={quantity} onChange={event=>setQuantity(event.target.value)} style={inputStyle}/></label><label style={fieldStyle}>Unit price (UGX)<input required type="number" min="1" step="0.01" value={unitPrice} onChange={event=>setUnitPrice(event.target.value)} style={inputStyle}/></label></div><button disabled={busy}>Issue invoice</button></form>
   <form onSubmit={recordPayment} style={cardStyle}><h2>Record payment</h2><p>Payments remain pending until an administrator reconciles them.</p><label style={fieldStyle}>Facility<select required value={paymentFacilityId} onChange={event=>setPaymentFacilityId(event.target.value)} style={inputStyle}><option value="">Select facility</option>{facilities.map(facility=><option key={facility.id} value={facility.id}>{facility.name}</option>)}</select></label><label style={fieldStyle}>Amount (UGX)<input required type="number" min="1" step="0.01" value={amount} onChange={event=>setAmount(event.target.value)} style={inputStyle}/></label><label style={fieldStyle}>Method<select value={method} onChange={event=>setMethod(event.target.value)} style={inputStyle}>{['Cash','Mobile Money','Bank Transfer'].map(item=><option key={item}>{item}</option>)}</select></label><button disabled={busy}>Record pending payment</button></form>
  </section>}
  <section style={cardStyle}><h2>Invoices</h2>{invoices.length===0?<p>No invoices issued yet.</p>:<div style={{overflowX:'auto'}}><table style={{width:'100%',borderCollapse:'collapse'}}><thead><tr><th align="left">Invoice</th><th align="left">Client</th><th align="left">Due</th><th align="left">Status</th><th align="right">Balance</th></tr></thead><tbody>{invoices.map(invoice=><tr key={invoice.id}><td>{invoice.invoice_number}</td><td>{invoice.facility_name}</td><td>{new Date(invoice.due_date+'T00:00:00').toLocaleDateString()}</td><td>{invoice.status.replace('_',' ')}</td><td align="right">{money(invoice.balance)}</td></tr>)}</tbody></table></div>}</section>
  <section style={cardStyle}><h2>Payments & receipts</h2>{payments.length===0?<p>No payments recorded yet.</p>:<div style={{display:'grid',gap:10}}>{payments.map(payment=><article key={payment.id} style={{borderTop:'1px solid #e2e8f0',paddingTop:12,display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}><div><strong>{payment.reference} · {payment.facility_name}</strong><p style={{margin:'5px 0'}}>{money(payment.amount)} · {payment.method} · {payment.status}</p>{payment.status==='confirmed'&&<small>Unallocated credit: {money(payment.unallocated_amount)}</small>}</div><div style={{display:'flex',gap:8,alignItems:'start',flexWrap:'wrap'}}>{payment.status==='pending'&&canConfirm&&<button onClick={()=>{setConfirming(payment);setInvoiceId('');setAllocation(payment.amount)}}>Reconcile</button>}{payment.status==='confirmed'&&<a href={'/api/accounts/payments/'+payment.id+'/receipt'} target="_blank" rel="noreferrer">Print receipt</a>}</div></article>)}</div>}</section>
  {confirming&&<section style={{...cardStyle,borderColor:'#16815b'}}><h2>Reconcile {confirming.reference}</h2><p>{confirming.facility_name} received {money(confirming.amount)}. Allocate it to one open invoice, or confirm it as unapplied credit.</p><form onSubmit={confirmPayment}><label style={fieldStyle}>Invoice allocation (optional)<select value={invoiceId} onChange={event=>setInvoiceId(event.target.value)} style={inputStyle}><option value="">Keep as unapplied credit</option>{openForSelectedPayment.map(invoice=><option key={invoice.id} value={invoice.id}>{invoice.invoice_number} · {money(invoice.balance)} outstanding</option>)}</select></label>{invoiceId&&<label style={fieldStyle}>Allocation amount (UGX)<input required type="number" min="0.01" max={confirming.amount} step="0.01" value={allocation} onChange={event=>setAllocation(event.target.value)} style={inputStyle}/></label>}<div style={{display:'flex',gap:10}}><button disabled={busy}>Confirm payment</button><button type="button" onClick={()=>setConfirming(null)}>Cancel</button></div></form></section>}
 </main>;
}
