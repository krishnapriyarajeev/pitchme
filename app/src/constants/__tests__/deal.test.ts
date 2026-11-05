import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { AUDIENCES, COMPOSURES, DEAL_STAGES, labelFor } from '@/constants/deal';

/** The keys in a Python tuple such as `STAGES = ("cold_call", ...)`. */
function backendKeys(name: string): string[] {
  const source = readFileSync(
    resolve(__dirname, '../../../../backend/ai/rehearsal/deal.py'),
    'utf8',
  );
  const tuple = new RegExp(`^${name} = \\(([^)]*)\\)`, 'm').exec(source);
  if (!tuple?.[1]) throw new Error(`${name} not found in deal.py`);
  return [...tuple[1].matchAll(/"([a-z_]+)"/g)].map((match) => match[1] ?? '');
}

describe('deal choices', () => {
  it.each([
    ['STAGES', DEAL_STAGES],
    ['AUDIENCES', AUDIENCES],
    ['COMPOSURES', COMPOSURES],
  ] as const)('%s match the API keys, in order', (name, choices) => {
    expect(choices.map((choice) => choice.key)).toEqual(backendKeys(name));
  });

  it('labels a key, and shows an unknown key in words', () => {
    expect(labelFor(DEAL_STAGES, 'cold_call')).toBe('Cold call');
    expect(labelFor(AUDIENCES, 'chief_of_staff')).toBe('Chief of staff');
    expect(labelFor(COMPOSURES, null)).toBe('');
  });
});
