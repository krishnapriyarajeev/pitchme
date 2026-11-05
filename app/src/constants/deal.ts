/**
 * The choices on the prepare screen.
 *
 * The keys are the API's keys (backend/ai/rehearsal/deal.py) and a test
 * checks that the two lists match. Each choice changes how the AI buyer
 * acts, so they are closed lists. Industry and competitors are free text.
 */

export type Choice<K extends string = string> = {
  key: K;
  label: string;
  /** One line under the label, where the label alone is not enough. */
  hint?: string;
};

export const DEAL_STAGES = [
  { key: 'cold_call', label: 'Cold call', hint: 'They did not expect your call' },
  { key: 'discovery', label: 'Discovery', hint: 'First real conversation' },
  { key: 'demo', label: 'Demo', hint: 'They want to see it work' },
  { key: 'proposal', label: 'Proposal', hint: 'They have your offer' },
  { key: 'negotiation', label: 'Negotiation', hint: 'Price and terms' },
  { key: 'closing', label: 'Closing', hint: 'Ready to decide' },
  { key: 'renewal', label: 'Renewal', hint: 'An existing customer' },
] as const satisfies readonly Choice[];

export const AUDIENCES = [
  { key: 'general', label: 'General buyer' },
  { key: 'ceo', label: 'CEO' },
  { key: 'cto', label: 'CTO' },
  { key: 'vp_sales', label: 'VP Sales' },
  { key: 'procurement', label: 'Procurement' },
  { key: 'product_manager', label: 'Product manager' },
  { key: 'investor', label: 'Investor' },
] as const satisfies readonly Choice[];

/**
 * How hard the buyer pushes, never how rude they are. Every one is a
 * professional the user could meet: impatient about price, maybe, but they
 * never mock or corner the seller.
 */
export const COMPOSURES = [
  { key: 'warm', label: 'Warm', hint: 'Open to a conversation' },
  { key: 'direct', label: 'Direct', hint: 'Low patience for fluff' },
  { key: 'analytical', label: 'Analytical', hint: 'Wants the numbers' },
  { key: 'guarded', label: 'Guarded', hint: 'Has been sold to before' },
] as const satisfies readonly Choice[];

/** Suggestions only; the API takes any industry. */
export const INDUSTRIES = [
  'Technology',
  'Financial services',
  'Healthcare',
  'Manufacturing',
  'Retail',
  'Education',
  'Other',
] as const;

export type DealStage = (typeof DEAL_STAGES)[number]['key'];
export type Audience = (typeof AUDIENCES)[number]['key'];
export type Composure = (typeof COMPOSURES)[number]['key'];

/**
 * The label for a key, for example "cold_call" to "Cold call". A key the app
 * does not know yet (a newer API) is shown in words rather than dropped.
 */
export function labelFor(choices: readonly Choice[], key: string | null | undefined): string {
  if (!key) return '';
  const found = choices.find((c) => c.key === key);
  if (found) return found.label;
  const words = key.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}
