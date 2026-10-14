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

const ID_TYPES = ['all', 'ssn_hash', 'bank_account_hash', 'email_hash', 'phone_hash', 'ip_address'];

function transformVelocity(rows: Record<string, unknown>[]) {
  return rows.map((r) => ({
    'Type': typeof r.identifier_type === 'string' ? fmt.humanize(r.identifier_type) : r.identifier_type,
    'Identifier': r.identifier_value,
    'Claims': r.distinct_claims,
    'States': r.distinct_states,
    'Claim IDs': r.claim_ids_str,
  }));
}

export function VelocityPage() {
  const [idType, setIdType] = useState('all');

  const parameters = useMemo(
    () => ({ identifier_type_filter: sql.string(idType) }),
    [idType],
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Velocity Clusters</h2>
        <p className="text-muted-foreground">Identifiers linked to multiple claims across state jurisdictions</p>
      </div>

      <div className="flex flex-wrap gap-4 items-end">
        <div className="space-y-1">
          <Label>Identifier Type</Label>
          <Select value={idType} onValueChange={setIdType}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ID_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t === 'all' ? 'All Types' : fmt.humanize(t)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {idType !== 'all' && (
          <Badge variant="outline" className="mb-1">
            {fmt.humanize(idType)}
          </Badge>
        )}
      </div>

      <DataTable
        queryKey="velocity_table"
        parameters={parameters}
        filterColumn="Identifier"
        filterPlaceholder="Search by identifier..."
        transform={transformVelocity}
      />
    </div>
  );
}
