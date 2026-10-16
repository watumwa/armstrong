import { NextResponse } from 'next/server';
import bcrypt from 'bcryptjs';
import {query} from '@/lib/server/db';
import {requireRole} from '@/lib/server/auth';
export const runtime='nodejs';
const roles=['Administrator','Supervisor','Waste Collector','Revenue Officer'];
export async function GET(){if(!await requireRole(['Administrator']))return NextResponse.json({error:'Forbidden'},{status:403});const result=await query('SELECT id,name,email,role,active,created_at FROM users ORDER BY created_at DESC');return NextResponse.json({users:result.rows})}
export async function POST(request:Request){if(!await requireRole(['Administrator']))return NextResponse.json({error:'Forbidden'},{status:403});try{const data=await request.json();const name=String(data.name||'').trim(),email=String(data.email||'').trim().toLowerCase(),role=String(data.role||''),password=String(data.password||'');if(name.length<2||!/^\S+@\S+\.\S+$/.test(email)||!roles.includes(role)||password.length<12)return NextResponse.json({error:'Valid name, email, role and password (12+ characters) required'},{status:400});const hash=await bcrypt.hash(password,12);const result=await query('INSERT INTO users(name,email,role,password_hash) VALUES($1,$2,$3,$4) RETURNING id,name,email,role,active,created_at',[name,email,role,hash]);return NextResponse.json({user:result.rows[0]},{status:201})}catch(e){if((e as {code?:string}).code==='23505')return NextResponse.json({error:'Email already registered'},{status:409});return NextResponse.json({error:'Could not create user'},{status:500})}}
