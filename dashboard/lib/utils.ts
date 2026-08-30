/**
 * Formatting utility functions for Modern Ledger design system.
 */

export function formatPaiseToINR(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return '—';
  const rupees = paise / 100;
  const formatted = Math.abs(rupees).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return rupees < 0 ? `-₹${formatted}` : `₹${formatted}`;
}

export function formatConfidencePercent(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined) return '100%';
  const pct = Math.round(confidence <= 1.0 ? confidence * 100 : confidence);
  return `${pct}%`;
}

export function formatTimestampTime(isoString: string): string {
  if (!isoString) return '--:--:--';
  try {
    const date = new Date(isoString);
    return date.toTimeString().split(' ')[0];
  } catch {
    return isoString;
  }
}

export function formatTimestampDateTime(isoString: string): string {
  if (!isoString) return '--';
  try {
    const date = new Date(isoString);
    return `${date.toISOString().split('T')[0]} ${date.toTimeString().split(' ')[0]}`;
  } catch {
    return isoString;
  }
}
