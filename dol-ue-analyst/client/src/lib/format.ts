const numberFmt = new Intl.NumberFormat('en-US');
const currencyFmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const currencyDetailFmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 });
const compactFmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 });

export const fmt = {
  number: (n: number) => numberFmt.format(n),
  currency: (n: number) => currencyFmt.format(n),
  currencyDetail: (n: number) => currencyDetailFmt.format(n),
  compact: (n: number) => compactFmt.format(n),
  pct: (n: number) => `${n.toFixed(1)}%`,
  humanize: (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
};

export function chartValueFormatter(value: string | number, field: string): string {
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(n)) return String(value);
  if (field.includes('amount') || field.includes('paid') || field.includes('payment')) return fmt.compact(n);
  return fmt.number(n);
}
