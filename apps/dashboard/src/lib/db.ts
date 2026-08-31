import pg from "pg";

const { Pool } = pg;

declare global {
  // eslint-disable-next-line no-var
  var __phase3DashboardPool: pg.Pool | undefined;
}

function sanitizedConnectionString(): string {
  const value = process.env.SUPABASE_DB_URL;
  if (!value) {
    throw new Error("Missing SUPABASE_DB_URL. Copy .env.local.example to .env.local and fill it in.");
  }

  const url = new URL(value);

  // Supabase pooler URLs often include sslmode=require. The node-postgres
  // parser can treat that differently from the explicit ssl object below, so
  // keep TLS handling in one place.
  url.searchParams.delete("sslmode");
  url.searchParams.delete("uselibpqcompat");

  return url.toString();
}

export function getPool(): pg.Pool {
  if (!globalThis.__phase3DashboardPool) {
    globalThis.__phase3DashboardPool = new Pool({
      connectionString: sanitizedConnectionString(),
      ssl: { rejectUnauthorized: false }
    });
  }

  return globalThis.__phase3DashboardPool;
}

/**
 * Execute one dashboard query inside an explicit PostgreSQL read-only
 * transaction.
 *
 * The Supabase connection path does not honor startup
 * default_transaction_read_only options consistently, so the dashboard
 * enforces its read-only contract at the shared query boundary instead.
 */
export async function queryRows<T>(
  sql: string,
  params: unknown[] = [],
): Promise<T[]> {
  const client = await getPool().connect();

  try {
    await client.query("begin read only");
    const result = await client.query(sql, params);
    await client.query("commit");
    return result.rows as T[];
  } catch (error) {
    try {
      await client.query("rollback");
    } catch {
      // Preserve the original query/transaction failure.
    }

    throw error;
  } finally {
    client.release();
  }
}
