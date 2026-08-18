/** Shared formatting for the admin panel.
 *
 * Extracted because status labels and money were being re-declared in every
 * admin screen, and a label that differs between the dashboard and the orders
 * table looks like two different systems.
 */

export const STATUS_LABELS = {
  received: 'Received',
  fabric_cut: 'Fabric cut',
  stitching: 'Stitching',
  qc: 'QC check',
  dispatched: 'Dispatched',
  cancelled: 'Cancelled',
};

/** Forward-only production workflow, mirroring the server's. The server still
 *  validates every transition — this only avoids offering a button that 409s. */
export const STAGES = ['received', 'fabric_cut', 'stitching', 'qc', 'dispatched'];
const TERMINAL = new Set(['dispatched', 'cancelled']);

export function nextStatuses(current) {
  if (TERMINAL.has(current)) return [];
  const index = STAGES.indexOf(current);
  const options = [];
  if (index >= 0 && index + 1 < STAGES.length) options.push(STAGES[index + 1]);
  options.push('cancelled');
  return options;
}

/** CSS modifier for a status badge. Underscores are kept so the class matches
 *  the status value exactly and a new stage can't silently lose its styling. */
export const statusClass = (status) => `status-${status}`;

export function money(value) {
  const number = Number(value ?? 0);
  // Compact above a million so a KPI card reads "LKR 1.2M" rather than
  // overflowing its box with nine digits.
  if (Math.abs(number) >= 1_000_000) {
    return `LKR ${(number / 1_000_000).toFixed(1)}M`;
  }
  return `LKR ${number.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export const moneyExact = (value) =>
  `LKR ${Number(value ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

export const shortDate = (value) =>
  new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
