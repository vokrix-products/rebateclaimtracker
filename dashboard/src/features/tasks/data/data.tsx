import {TriangleAlert, Clock, CircleCheckBig} from 'lucide-react'

export const labels = [
  {
    value: 'bug',
    label: 'Bug',
  },
  {
    value: 'feature',
    label: 'Feature',
  },
  {
    value: 'documentation',
    label: 'Documentation',
  },
]

// Severity tiers drive badge color. Every status maps to exactly one tier:
//   critical -> red (destructive)   e.g. expired, denied, failed
//   warning  -> amber (warning)     e.g. expiring soon, needs review
//   good     -> green (success)     e.g. valid, approved, done
//   neutral  -> gray (secondary)    e.g. pending, queued, n/a
export type Severity = 'critical' | 'warning' | 'good' | 'neutral' | 'info'

export const severityToBadgeVariant: Record<Severity, 'destructive' | 'warning' | 'success' | 'secondary'> = {
  critical: 'destructive',
  warning: 'warning',
  good: 'success',
  neutral: 'secondary',
  info: 'secondary',
}

// PRODUCT_CUSTOMIZE: replace this list with the real statuses this product
// produces (must match exactly what the backend poller writes to
// records.status). Every status must declare a severity tier above. Default
// values below are generic placeholders only — do not ship as-is.
// __STATUSES_BLOCK_START__
export const statuses: {
  label: string
  value: string
  icon: typeof TriangleAlert
  severity: Severity
}[] = [
  { label: 'Missing Agreement', value: 'missing_agreement:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Missing Purchase Data', value: 'missing_purchase_data:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Missing Required Claim Document', value: 'missing_required_claim_document:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Unparsed Agreement Line', value: 'unparsed_agreement_line:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Expired Claim Window', value: 'expired_claim_window:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Valid Earned Unclaimed', value: 'valid_earned_unclaimed:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Claim Window Open', value: 'claim_window_open:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'Claim Window Closing Soon', value: 'claim_window_closing_soon:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Submitted', value: 'submitted:info', icon: Clock, severity: 'info' as Severity },
  { label: 'Approved', value: 'approved:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'Partially Paid', value: 'partially_paid:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Paid', value: 'paid:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'Denied', value: 'denied:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Disputed', value: 'disputed:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Flagged For Review', value: 'flagged_for_review:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Threshold Gap', value: 'threshold_gap:info', icon: Clock, severity: 'info' as Severity },
  { label: 'Threshold Reached', value: 'threshold_reached:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'Unreconciled Gap', value: 'unreconciled_gap:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Reconciled', value: 'reconciled:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'No Activity', value: 'no_activity:info', icon: Clock, severity: 'info' as Severity },
]
// __STATUSES_BLOCK_END__
