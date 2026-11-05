import type { Band } from '@/constants/bands';
import type { AnalysisResult, CorrectedAnswer, Finding, Severity } from '@/lib/api';

/**
 * Turns an analysis result into what the debrief shows. Pure, so the rules
 * that decide what the user reads are tested on their own.
 */

export type Verdict = 'handled' | 'weak' | 'dodged' | 'inaccurate' | 'unsupported';

/** Every verdict is a next step, never a mark against the user. */
export const VERDICTS: Record<Verdict, { label: string; band: Band }> = {
  handled: { label: 'Handled', band: 'strong' },
  weak: { label: 'Could be stronger', band: 'steady' },
  dodged: { label: 'Answer it next time', band: 'focus' },
  inaccurate: { label: 'Check the facts', band: 'focus' },
  unsupported: { label: 'Not in your playbook', band: 'focus' },
};

export type Objection = {
  question: string;
  /** What the user said; empty when they did not answer. */
  said: string;
  verdict: Verdict;
  why: string;
  /** From the playbook, when the judge used it. */
  evidence: string;
  atMs: number | null;
  stronger: CorrectedAnswer | null;
};

const SEVERITY_RANK: Record<Severity, number> = { high: 3, medium: 2, low: 1, info: 0 };

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function same(a: string, b: string): boolean {
  const clean = (s: string) =>
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  return clean(a) !== '' && clean(a) === clean(b);
}

function isVerdict(category: string): category is Verdict {
  return category in VERDICTS;
}

/**
 * The buyer's questions and objections, worst first, each with the stronger
 * answer the API wrote for it, when there is one.
 */
export function objections(
  result: Pick<AnalysisResult, 'findings' | 'corrected_answers'>,
): Objection[] {
  return result.findings
    .filter((f) => f.pipeline === 'content' && isVerdict(f.category))
    .sort((a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity])
    .map((finding) => {
      const question = text(finding.details.customer_quote);
      const said = text(finding.details.agent_quote);
      const stronger =
        result.corrected_answers.find(
          (answer) =>
            same(answer.question, question) || (said !== '' && same(answer.original, said)),
        ) ?? null;
      return {
        question,
        said,
        verdict: finding.category as Verdict,
        why: finding.summary,
        evidence: text(finding.details.reference_evidence),
        atMs: finding.note?.t_start_ms ?? null,
        stronger,
      };
    });
}

/** Claims the playbook does not back, or gets wrong: the pitch-integrity list. */
export function integrityIssues(items: Objection[]): Objection[] {
  return items.filter((item) => item.verdict === 'inaccurate' || item.verdict === 'unsupported');
}

/** Speech, voice and body-language findings worth acting on, worst first. */
export function deliveryFindings(findings: Finding[]): Finding[] {
  return findings
    .filter((f) => f.pipeline !== 'content' && f.severity !== 'info')
    .sort((a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity]);
}

/** The comfortable speaking pace, as the speech report uses it. */
export const PACE_RANGE = { low: 110, high: 170 } as const;
