import type { CorrectedAnswer, Finding } from '@/lib/api';
import { deliveryFindings, integrityIssues, objections, VERDICTS } from '@/lib/debrief';

function content(
  category: string,
  severity: Finding['severity'],
  question: string,
  said = '',
): Finding {
  return {
    pipeline: 'content',
    category,
    severity,
    summary: `${category} reason`,
    note: { t_start_ms: 12_000, t_end_ms: 15_000, quote: said },
    details: { customer_quote: question, agent_quote: said, reference_evidence: '' },
  };
}

const answer: CorrectedAnswer = {
  question: 'What does it cost per seat?',
  original: 'It is affordable.',
  stronger: 'It is 40 dollars a seat, billed yearly.',
  change: 'Gave the price.',
  citation: 'Pricing: 40 USD per seat',
  verified: true,
  unsupported_numbers: [],
  t_start_ms: 12_000,
  audio_url: null,
};

describe('objections', () => {
  const findings = [
    content('handled', 'info', 'Who else uses it?', 'Three banks.'),
    content('dodged', 'high', 'What does it cost per seat?', 'It is affordable.'),
    content('no_questions', 'info', ''),
    { ...content('weak', 'low', 'x'), pipeline: 'speech' },
  ];

  it('lists the content verdicts, worst first, with the stronger answer', () => {
    const items = objections({ findings, corrected_answers: [answer] });
    expect(items.map((item) => item.verdict)).toEqual(['dodged', 'handled']);
    expect(items[0]).toMatchObject({
      question: 'What does it cost per seat?',
      said: 'It is affordable.',
      atMs: 12_000,
      stronger: answer,
    });
    expect(items[1]?.stronger).toBeNull();
  });

  it('matches a stronger answer by the question, whatever its punctuation', () => {
    const items = objections({
      findings: [content('weak', 'medium', 'what does it COST per seat')],
      corrected_answers: [answer],
    });
    expect(items[0]?.stronger).toBe(answer);
  });

  it('keeps only accuracy problems for pitch integrity', () => {
    const items = objections({
      findings: [
        content('inaccurate', 'high', 'Price?', '30 dollars'),
        content('unsupported', 'medium', 'SOC 2?', 'Yes'),
        content('weak', 'low', 'Timeline?', 'Soon'),
      ],
      corrected_answers: [],
    });
    expect(integrityIssues(items).map((item) => item.verdict)).toEqual([
      'inaccurate',
      'unsupported',
    ]);
  });

  it('labels every verdict as a next step', () => {
    const labels = Object.values(VERDICTS).map((v) => v.label.toLowerCase());
    expect(labels.join(' ')).not.toMatch(/fail|bad|poor|wrong/);
  });
});

it('lists delivery findings worth acting on, worst first', () => {
  const speech = (category: string, severity: Finding['severity']): Finding => ({
    pipeline: 'speech',
    category,
    severity,
    summary: category,
    note: null,
    details: {},
  });
  const result = deliveryFindings([
    speech('pace_too_slow', 'low'),
    speech('ok', 'info'),
    { ...speech('looking_away', 'medium'), pipeline: 'vision' },
    content('dodged', 'high', 'q'),
  ]);
  expect(result.map((f) => f.category)).toEqual(['looking_away', 'pace_too_slow']);
});
