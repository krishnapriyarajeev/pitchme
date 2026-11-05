import {
  dealTitle,
  fileKind,
  formatBytes,
  formatClock,
  formatDuration,
  formatMoment,
  formatRelativeDay,
  formatShortDate,
  initialsOf,
} from '@/lib/format';

describe('formatDuration', () => {
  it('shows seconds alone under a minute', () => {
    expect(formatDuration(42)).toBe('42 s');
  });

  it('pads the seconds after minutes', () => {
    expect(formatDuration(184)).toBe('3 min 04 s');
  });

  it('rounds the fractional seconds the API sends', () => {
    expect(formatDuration(73.6)).toBe('1 min 14 s');
  });

  it('never goes below zero', () => {
    expect(formatDuration(-5)).toBe('0 s');
  });
});

describe('clocks', () => {
  it('formats a running timer', () => {
    expect(formatClock(0)).toBe('0:00');
    expect(formatClock(725.9)).toBe('12:05');
  });

  it('formats a moment in milliseconds', () => {
    expect(formatMoment(65_400)).toBe('1:05');
  });
});

describe('days', () => {
  const now = new Date(2026, 10, 5, 15, 0);

  it('names today and yesterday', () => {
    expect(formatRelativeDay(new Date(2026, 10, 5, 8, 0).toISOString(), now)).toBe('Today');
    expect(formatRelativeDay(new Date(2026, 10, 4, 23, 0).toISOString(), now)).toBe('Yesterday');
  });

  it('names the weekday within the last week', () => {
    expect(formatRelativeDay(new Date(2026, 10, 2, 9, 0).toISOString(), now)).toBe('Monday');
  });

  it('gives a date after a week, with the year only when it differs', () => {
    expect(formatRelativeDay(new Date(2026, 9, 20).toISOString(), now)).toBe('20 Oct');
    expect(formatShortDate(new Date(2025, 0, 3).toISOString(), now)).toBe('3 Jan 2025');
  });

  it('gives nothing for a bad date', () => {
    expect(formatRelativeDay('not a date', now)).toBe('');
  });
});

describe('files', () => {
  it('formats sizes with one decimal at most', () => {
    expect(formatBytes(undefined)).toBe('');
    expect(formatBytes(900)).toBe('900 B');
    expect(formatBytes(2048)).toBe('2 KB');
    expect(formatBytes(2.45 * 1024 * 1024)).toBe('2.5 MB');
  });

  it('names the file type from the extension', () => {
    expect(fileKind('playbook.pdf')).toBe('PDF');
    expect(fileKind('README')).toBe('File');
    expect(fileKind('.env')).toBe('File');
  });
});

describe('dealTitle', () => {
  it('joins the prospect and company', () => {
    expect(dealTitle('Jo Bennett', 'Saber Industries')).toBe('Jo Bennett · Saber Industries');
    expect(dealTitle('Jo Bennett', ' ')).toBe('Jo Bennett');
  });
});

describe('initialsOf', () => {
  it('takes the first and last name', () => {
    expect(initialsOf('jo anne bennett')).toBe('JB');
    expect(initialsOf('Cher')).toBe('C');
    expect(initialsOf('  ')).toBe('');
    expect(initialsOf(null)).toBe('');
  });
});
