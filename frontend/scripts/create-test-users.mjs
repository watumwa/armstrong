/**
 * Provision temporary TEST accounts for all five Armstrong roles.
 * Run on an isolated development database only, after schema.sql.
 * Passwords are generated at runtime and printed once. Never commit them.
 * Refuses to run unless ALLOW_TEST_USERS=yes and NODE_ENV != production.
 */
import pg from 'pg';
import bcrypt from 'bcryptjs';
import {randomBytes} from 'node:crypto';
if(process.env.ALLOW_TEST_USERS!=='yes'||process.env.NODE_ENV==='production')throw new Error('Test users disabled. Set ALLOW_TEST_USERS=yes in a non-production environment.');
if(!process.env.DATABASE_URL)throw new Error('DATABASE_URL is required');
const accounts=[
{role:'Administrator',name:'Test Administrator',email:'admin.test@armstrong.example'},
{role:'Supervisor',name:'Test Supervisor',email:'supervisor.test@armstrong.example'},
{role:'Waste Collector',name:'Test Collector',email:'collector.test@armstrong.example'},
{role:'Revenue Officer',name:'Test Revenue Officer',email:'revenue.test@armstrong.example'},
{role:'Marketer',name:'Test Marketer',email:'marketer.test@armstrong.example'}
];
const pool=new pg.Pool({connectionString:process.env.DATABASE_URL,max:1});
try{
const existing=await pool.query('SELECT COUNT(*)::int AS count FROM users');
if(existing.rows[0].count!==0)throw new Error('Test provisioning requires an empty users table to prevent modifying real accounts.');
const created=[];
for(const account of accounts){const password=randomBytes(18).toString('base64url');const hash=await bcrypt.hash(password,12);await pool.query('INSERT INTO users(name,email,role,password_hash) VALUES($1,$2,$3,$4)',[account.name,account.email,account.role,hash]);created.push({...account,password})}
console.log('\nTEST ACCOUNTS — COPY TO A SECURE PASSWORD MANAGER; DISPLAYED ONLY NOW\n');
for(const u of created)console.log(u.role+'\n  Email: '+u.email+'\n  Password: '+u.password+'\n');
console.log('These accounts exist ONLY in the database used for this command. Never use them for production.');
}finally{await pool.end()}
