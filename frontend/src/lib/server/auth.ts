import { cookies } from 'next/headers';
import { SignJWT,jwtVerify } from 'jose';
export type Role='Administrator'|'Supervisor'|'Waste Collector'|'Revenue Officer';
export type Session={id:string;role:Role;name:string};
const cookie='armstrong_session';
function key(){const s=process.env.AUTH_SECRET;if(!s||s.length<32)throw new Error('AUTH_SECRET must be at least 32 characters');return new TextEncoder().encode(s)}
export async function issueSession(s:Session){return new SignJWT({role:s.role,name:s.name}).setProtectedHeader({alg:'HS256'}).setSubject(s.id).setIssuedAt().setExpirationTime('8h').sign(key())}
export async function getSession():Promise<Session|null>{try{const token=(await cookies()).get(cookie)?.value;if(!token)return null;const {payload}=await jwtVerify(token,key());if(typeof payload.sub!=='string'||typeof payload.role!=='string'||typeof payload.name!=='string')return null;return {id:payload.sub,role:payload.role as Role,name:payload.name}}catch{return null}}
export async function requireRole(roles:Role[]){const session=await getSession();return session&&roles.includes(session.role)?session:null}
export const sessionCookie=cookie;
