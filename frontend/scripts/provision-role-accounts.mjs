import pg from 'pg';
import bcrypt from 'bcryptjs';
import { randomBytes } from 'node:crypto';

if (process.env.CONFIRM_PRODUCTION_ACCOUNTS !== 'yes') {
  throw new Error('Set CONFIRM_PRODUCTION_ACCOUNTS=yes to authorize provisioning.');
}

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL is required.');
}

const accounts = [
  { role: 'Administrator', name: 'Test Administrator', email: 'admin@armstrong.test' },
  { role: 'Supervisor', name: 'Test Supervisor', email: 'supervisor@armstrong.test' },
  { role: 'Waste Collector', name: 'Test Waste Collector', email: 'collector@armstrong.test' },
  { role: 'Revenue Officer', name: 'Test Revenue Officer', email: 'revenue@armstrong.test' },
];

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  max: 1,
  connectionTimeoutMillis: 10000,
});

try {
  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    const created = [];
    const skipped = [];

    for (const account of accounts) {
      const password = randomBytes(24).toString('base64url');
      const hash = await bcrypt.hash(password, 12);

      const result = await client.query(
        `INSERT INTO users (name, email, role, password_hash)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (email) DO NOTHING
         RETURNING email`,
        [account.name, account.email, account.role, hash]
      );

      if (result.rowCount === 1) {
        created.push({ ...account, password });
      } else {
        skipped.push(account.email);
      }
    }

    await client.query('COMMIT');

    console.log('\nACCOUNTS CREATED:\n');

    for (const account of created) {
      console.log(`${account.role}`);
      console.log(`Email: ${account.email}`);
      console.log(`Temporary password: ${account.password}\n`);
    }

    console.log('Existing accounts skipped:', skipped.length);
    for (const email of skipped) console.log(`- ${email}`);

    console.log(`\nCreated ${created.length} account(s).`);
    console.log('Save new passwords securely. They will not be displayed again.');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
} finally {
  await pool.end();
}
