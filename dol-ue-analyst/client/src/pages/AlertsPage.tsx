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

const ALERT_TYPES = ['all', 'ssn_mismatch', 'identity_crossmatch', 'wage_discrepancy', 'address_mismatch', 'employer_mismatch'];

function transformAlerts(rows: Record<string, unknown>[]) {
  return rows.map((r) => ({
    'Claim ID': r.claim_id,
    'Alert Type': typeof r.alert_type === 'string' ? fmt.humanize(r.alert_type) : r.alert_type,
    'Detail': r.alert_detail,
    'State': r.source_state,
    'Filed Date': r.filed_date,
    'Risk Score': typeof r.risk_score === 'number' ? Math.round(r.risk_score) : r.risk_score,
  }));
}

export function AlertsPage() {
  const [alertType, setAlertType] = useState('all');

  const parameters = useMemo(
    () => ({ alert_type_filter: sql.string(alertType) }),
    [alertType],
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Crossmatch Alerts</h2>
        <p className="text-muted-foreground">Identity and data crossmatch alerts flagged during claims processing</p>
      </div>

      <div className="flex flex-wrap gap-4 items-end">
        <div className="space-y-1">
          <Label>Alert Type</Label>
          <Select value={alertType} onValueChange={setAlertType}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ALERT_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t === 'all' ? 'All Types' : fmt.humanize(t)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {alertType !== 'all' && (
          <Badge variant="outline" className="mb-1">
            {fmt.humanize(alertType)}
          </Badge>
        )}
      </div>

      <DataTable
        queryKey="alerts_table"
        parameters={parameters}
        filterColumn="Claim ID"
        filterPlaceholder="Search by claim ID..."
        transform={transformAlerts}
      />
    </div>
  );
}
