// Run only after schema.sql is applied. Never commit credentials.
import pg from 'pg';import bcrypt from 'bcryptjs';
const {DATABASE_URL,ADMIN_EMAIL,ADMIN_NAME,ADMIN_PASSWORD}=process.env;
if(!DATABASE_URL||!ADMIN_EMAIL||!ADMIN_NAME||!ADMIN_PASSWORD||ADMIN_PASSWORD.length<12)throw new Error('Set DATABASE_URL, ADMIN_EMAIL, ADMIN_NAME, ADMIN_PASSWORD (12+ characters)');
const pool=new pg.Pool({connectionString:DATABASE_URL,max:1});
try{const count=await pool.query("SELECT COUNT(*)::int AS count FROM users WHERE role='Administrator'");if(count.rows[0].count>0)throw new Error('Administrator already exists. Bootstrap disabled.');const hash=await bcrypt.hash(ADMIN_PASSWORD,12);await pool.query("INSERT INTO users(name,email,role,password_hash) VALUES($1,$2,'Administrator',$3)",[ADMIN_NAME,ADMIN_EMAIL.toLowerCase(),hash]);console.log('Initial administrator created. Remove bootstrap secrets after setup.')}finally{await pool.end()}
