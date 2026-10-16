import { Pool, type QueryResultRow } from 'pg';
let pool:Pool|undefined;
export function database(){if(!process.env.DATABASE_URL)throw new Error('DATABASE_URL is not configured');if(!pool)pool=new Pool({connectionString:process.env.DATABASE_URL,max:3,connectionTimeoutMillis:5000,ssl:process.env.DATABASE_SSL==='require'?{rejectUnauthorized:true}:undefined});return pool}
export async function query<T extends QueryResultRow=QueryResultRow>(sql:string,params:unknown[]=[]){return database().query<T>(sql,params)}
