import { REVIEW_STAGES, stageStates } from '@/lib/review';

describe('stageStates', () => {
  it('starts nothing while queued', () => {
    expect(stageStates({ status: 'queued', stage: null })).toEqual(
      REVIEW_STAGES.map(() => 'pending'),
    );
  });

  it('marks the reported stage and those before it', () => {
    expect(stageStates({ status: 'running', stage: 'analyzing' })).toEqual([
      'done',
      'done',
      'active',
      'pending',
    ]);
  });

  it('treats an unknown stage as the first', () => {
    expect(stageStates({ status: 'running', stage: 'something_new' })[0]).toBe('active');
  });

  it('finishes every stage when complete', () => {
    expect(stageStates({ status: 'complete', stage: null })).toEqual(
      REVIEW_STAGES.map(() => 'done'),
    );
  });
});
