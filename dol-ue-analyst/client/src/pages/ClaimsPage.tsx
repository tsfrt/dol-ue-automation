import { useState, useMemo } from 'react';
import {
  DataTable,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Label,
  Badge,
} from '@databricks/appkit-ui/react';
import { sql } from '@databricks/appkit-ui/js';
import { fmt } from '../lib/format';

const STATES = ['all', 'CA', 'WA', 'TX', 'IL', 'OH', 'FL', 'GA', 'NY', 'NJ', 'PA'];
const RISK_LEVELS = ['all', 'low', 'medium', 'high'];

function transformClaims(rows: Record<string, unknown>[]) {
  return rows.map((r) => ({
    'Claim ID': r.claim_id,
    'State': r.source_state,
    'Filed Date': r.filed_date,
    'Risk Score': typeof r.risk_score === 'number' ? Math.round(r.risk_score) : r.risk_score,
    'Risk Level': typeof r.risk_level === 'string' ? fmt.humanize(r.risk_level) : r.risk_level,
    'Payment': typeof r.payment_amount === 'number' ? fmt.currencyDetail(r.payment_amount) : r.payment_amount,
    'Fraud Status': r.gt_is_fraud === true || r.gt_is_fraud === 'true' ? 'Fraud' : 'Clean',
    'Reason Codes': typeof r.reason_codes === 'string' ? fmt.humanize(r.reason_codes) : r.reason_codes,
  }));
}

export function ClaimsPage() {
  const [stateFilter, setStateFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');

  const parameters = useMemo(
    () => ({ state_filter: sql.string(stateFilter), risk_filter: sql.string(riskFilter) }),
    [stateFilter, riskFilter],
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Claims Explorer</h2>
        <p className="text-muted-foreground">Browse and filter individual unemployment insurance claims</p>
      </div>

      <div className="flex flex-wrap gap-4 items-end">
        <div className="space-y-1">
          <Label>State</Label>
          <Select value={stateFilter} onValueChange={setStateFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATES.map((s) => (
                <SelectItem key={s} value={s}>{s === 'all' ? 'All States' : s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label>Risk Level</Label>
          <Select value={riskFilter} onValueChange={setRiskFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {RISK_LEVELS.map((r) => (
                <SelectItem key={r} value={r}>{r === 'all' ? 'All Levels' : r.charAt(0).toUpperCase() + r.slice(1)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {(stateFilter !== 'all' || riskFilter !== 'all') && (
          <Badge variant="outline" className="mb-1">
            Filtered
          </Badge>
        )}
      </div>

      <DataTable
        queryKey="claims_table"
        parameters={parameters}
        filterColumn="Claim ID"
        filterPlaceholder="Search by claim ID..."
        transform={transformClaims}
      />
    </div>
  );
}
