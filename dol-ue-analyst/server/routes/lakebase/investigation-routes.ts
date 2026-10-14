import { z } from 'zod';
import { Application } from 'express';

interface AppKitWithLakebase {
  lakebase: {
    query(text: string, params?: unknown[]): Promise<{ rows: Record<string, unknown>[] }>;
  };
  server: {
    extend(fn: (app: Application) => void): void;
  };
}

const TABLE_EXISTS_SQL = `
  SELECT 1 FROM information_schema.tables
  WHERE table_schema = 'fraud_app' AND table_name = 'investigations'
`;

const SETUP_SQL = `CREATE SCHEMA IF NOT EXISTS fraud_app`;

const CREATE_TABLE_SQL = `
  CREATE TABLE IF NOT EXISTS fraud_app.investigations (
    id SERIAL PRIMARY KEY,
    claim_id TEXT NOT NULL,
    analyst TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  )
`;

const CreateInvestigation = z.object({
  claim_id: z.string().min(1),
  analyst: z.string().min(1),
  priority: z.enum(['low', 'medium', 'high', 'critical']).default('medium'),
  notes: z.string().optional(),
});

const UpdateInvestigation = z.object({
  status: z.enum(['open', 'in_review', 'escalated', 'resolved', 'dismissed']).optional(),
  priority: z.enum(['low', 'medium', 'high', 'critical']).optional(),
  notes: z.string().optional(),
});

export async function setupInvestigationRoutes(appkit: AppKitWithLakebase) {
  try {
    const { rows } = await appkit.lakebase.query(TABLE_EXISTS_SQL);
    if (rows.length > 0) {
      console.log('[lakebase] Table fraud_app.investigations already exists');
    } else {
      await appkit.lakebase.query(SETUP_SQL);
      await appkit.lakebase.query(CREATE_TABLE_SQL);
      console.log('[lakebase] Created fraud_app.investigations');
    }
  } catch (err) {
    console.warn('[lakebase] Setup failed:', (err as Error).message);
    console.warn('[lakebase] Routes registered but may return errors until deployed');
  }

  appkit.server.extend((app) => {
    app.get('/api/investigations', async (req, res) => {
      try {
        const status = req.query.status as string | undefined;
        let sql = 'SELECT * FROM fraud_app.investigations';
        const params: unknown[] = [];
        if (status && status !== 'all') {
          sql += ' WHERE status = $1';
          params.push(status);
        }
        sql += ' ORDER BY created_at DESC LIMIT 200';
        const { rows } = await appkit.lakebase.query(sql, params);
        res.json(rows);
      } catch (err) {
        console.error('Failed to list investigations:', err);
        res.status(500).json({ error: 'Failed to list investigations' });
      }
    });

    app.get('/api/investigations/claim/:claimId', async (req, res) => {
      try {
        const { rows } = await appkit.lakebase.query(
          'SELECT * FROM fraud_app.investigations WHERE claim_id = $1 ORDER BY created_at DESC',
          [req.params.claimId],
        );
        res.json(rows);
      } catch (err) {
        console.error('Failed to get investigations:', err);
        res.status(500).json({ error: 'Failed to get investigations' });
      }
    });

    app.post('/api/investigations', async (req, res) => {
      try {
        const parsed = CreateInvestigation.safeParse(req.body);
        if (!parsed.success) {
          res.status(400).json({ error: parsed.error.message });
          return;
        }
        const { claim_id, analyst, priority, notes } = parsed.data;
        const { rows } = await appkit.lakebase.query(
          `INSERT INTO fraud_app.investigations (claim_id, analyst, priority, notes)
           VALUES ($1, $2, $3, $4) RETURNING *`,
          [claim_id, analyst, priority, notes || null],
        );
        res.status(201).json(rows[0]);
      } catch (err) {
        console.error('Failed to create investigation:', err);
        res.status(500).json({ error: 'Failed to create investigation' });
      }
    });

    app.patch('/api/investigations/:id', async (req, res) => {
      try {
        const id = parseInt(req.params.id, 10);
        if (isNaN(id)) {
          res.status(400).json({ error: 'Invalid id' });
          return;
        }
        const parsed = UpdateInvestigation.safeParse(req.body);
        if (!parsed.success) {
          res.status(400).json({ error: parsed.error.message });
          return;
        }
        const updates: string[] = [];
        const params: unknown[] = [];
        let idx = 1;
        if (parsed.data.status) {
          updates.push(`status = $${idx++}`);
          params.push(parsed.data.status);
        }
        if (parsed.data.priority) {
          updates.push(`priority = $${idx++}`);
          params.push(parsed.data.priority);
        }
        if (parsed.data.notes !== undefined) {
          updates.push(`notes = $${idx++}`);
          params.push(parsed.data.notes);
        }
        if (updates.length === 0) {
          res.status(400).json({ error: 'No fields to update' });
          return;
        }
        updates.push(`updated_at = NOW()`);
        params.push(id);
        const { rows } = await appkit.lakebase.query(
          `UPDATE fraud_app.investigations SET ${updates.join(', ')} WHERE id = $${idx} RETURNING *`,
          params,
        );
        if (rows.length === 0) {
          res.status(404).json({ error: 'Not found' });
          return;
        }
        res.json(rows[0]);
      } catch (err) {
        console.error('Failed to update investigation:', err);
        res.status(500).json({ error: 'Failed to update investigation' });
      }
    });
  });
}
