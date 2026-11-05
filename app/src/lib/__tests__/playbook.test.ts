import { checkPlaybook, PLAYBOOK_MAX_BYTES, playbookKind } from '@/lib/playbook';

describe('checkPlaybook', () => {
  it('takes the types the API can read', () => {
    for (const name of ['deck.pptx', 'Pricing.PDF', 'notes.txt', 'battlecards.docx']) {
      expect(checkPlaybook({ name, size: 1000 })).toBeNull();
    }
  });

  it('names the type it cannot read', () => {
    expect(checkPlaybook({ name: 'sheet.xlsx' })).toBe(
      'PitchMe cannot read XLSX files. Use a PDF, PPTX, DOCX or TXT file.',
    );
  });

  it('refuses a file over the limit, with its size', () => {
    expect(checkPlaybook({ name: 'deck.pdf', size: PLAYBOOK_MAX_BYTES + 1 })).toBe(
      'This file is 25.0 MB. Use a file of 25 MB or less.',
    );
  });
});

it('reads the stored type from the presigned address', () => {
  expect(playbookKind('http://s3/pitchme/users/u/profile/playbook.pdf?X-Amz-Signature=abc')).toBe(
    'PDF',
  );
  expect(playbookKind(null)).toBe('File');
});
