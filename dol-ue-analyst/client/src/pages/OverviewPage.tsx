import { useMemo } from 'react';
import {
  useAnalyticsQuery,
  BarChart,
  LineChart,
  DonutChart,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Skeleton,
  Separator,
} from '@databricks/appkit-ui/react';
import { FileText, ShieldAlert, DollarSign, Target } from 'lucide-react';
import { fmt, chartValueFormatter } from '../lib/format';

function KpiCard({
  title,
  value,
  subtitle,
  badge,
  badgeVariant,
  icon: Icon,
  accent,
}: {
  title: string;
  value: string;
  subtitle?: string;
  badge?: string;
  badgeVariant?: 'default' | 'destructive' | 'secondary' | 'outline';
  icon: typeof FileText;
  accent: string;
}) {
  return (
    <Card className={`border-l-4 ${accent}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tracking-tight">{value}</div>
        <div className="flex items-center gap-2 mt-1">
          {badge && <Badge variant={badgeVariant ?? 'secondary'}>{badge}</Badge>}
          {subtitle && <span className="text-xs text-muted-foreground">{subtitle}</span>}
        </div>
      </CardContent>
    </Card>
  );
}

const CLAIMS_COLORS = ['hsl(221, 83%, 53%)', 'hsl(0, 84%, 60%)'];
const RISK_COLORS = ['hsl(142, 71%, 45%)', 'hsl(38, 92%, 50%)', 'hsl(0, 84%, 60%)'];

export function OverviewPage() {
  const params = useMemo(() => ({}), []);
  const { data, loading, error } = useAnalyticsQuery('state_summary', params);

  const totalClaims = data?.reduce((s, r) => s + r.total_claims, 0) ?? 0;
  const flaggedClaims = data?.reduce((s, r) => s + r.flagged_claims, 0) ?? 0;
  const totalPayments = data?.reduce((s, r) => s + r.total_payment_amount, 0) ?? 0;
  const actualFraud = data?.reduce((s, r) => s + r.actual_fraud_count, 0) ?? 0;
  const truePositives = data?.reduce((s, r) => s + r.true_positives, 0) ?? 0;
  const flagRate = totalClaims > 0 ? (flaggedClaims / totalClaims) * 100 : 0;
  const detectionRate = actualFraud > 0 ? (truePositives / actualFraud) * 100 : 0;

  const weeklyParams = useMemo(() => ({}), []);
  const riskParams = useMemo(() => ({}), []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Overview</h2>
        <p className="text-muted-foreground">Fraud detection metrics across {data?.length ?? '...'} state jurisdictions</p>
      </div>

      {error && <div className="text-destructive bg-destructive/10 p-3 rounded-md text-sm">Error: {error}</div>}

      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="border-l-4 border-l-muted">
              <CardHeader className="pb-2"><Skeleton className="h-4 w-24" /></CardHeader>
              <CardContent><Skeleton className="h-8 w-20" /></CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            title="Total Claims"
            value={fmt.number(totalClaims)}
            subtitle={`across ${data?.length ?? 0} states`}
            icon={FileText}
            accent="border-l-primary"
          />
          <KpiCard
            title="Flagged Claims"
            value={fmt.number(flaggedClaims)}
            badge={fmt.pct(flagRate)}
            badgeVariant="destructive"
            subtitle="flag rate"
            icon={ShieldAlert}
            accent="border-l-destructive"
          />
          <KpiCard
            title="Total Payments"
            value={fmt.compact(totalPayments)}
            subtitle="across all states"
            icon={DollarSign}
            accent="border-l-[hsl(var(--warning))]"
          />
          <KpiCard
            title="Detection Rate"
            value={fmt.pct(detectionRate)}
            badge={`${truePositives} of ${actualFraud}`}
            badgeVariant="secondary"
            subtitle="fraud cases caught"
            icon={Target}
            accent="border-l-[hsl(var(--success))]"
          />
        </div>
      )}

      <Separator />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Claims by State</CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              queryKey="state_summary"
              parameters={params}
              xKey="source_state"
              yKey={['total_claims', 'flagged_claims']}
              height={300}
              colors={CLAIMS_COLORS}
              showLegend
              valueFormatter={chartValueFormatter}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Weekly Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart
              queryKey="weekly_kpis"
              parameters={weeklyParams}
              xKey="week_ending"
              yKey={['claims_filed', 'fraud_claims_filed', 'payments_made']}
              height={300}
              showLegend
              valueFormatter={chartValueFormatter}
            />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risk Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              queryKey="risk_distribution"
              parameters={riskParams}
              xKey="risk_level"
              yKey="claim_count"
              height={280}
              colors={RISK_COLORS}
              valueFormatter={chartValueFormatter}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risk Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <DonutChart
              queryKey="risk_distribution"
              parameters={riskParams}
              xKey="risk_level"
              yKey="claim_count"
              height={280}
              colors={RISK_COLORS}
              showLegend
              valueFormatter={chartValueFormatter}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
