import { EmptyState } from '@/components/ui/empty-state';
import { Screen, ScreenHeader } from '@/components/ui/screen';

export default function PlaybookTab() {
  return (
    <Screen scroll edges={['top']}>
      <ScreenHeader title="Playbook" leading="none" />
      <EmptyState
        icon="book"
        title="No playbook yet"
        body="Add your sales playbook so the debrief can check your answers against it."
      />
    </Screen>
  );
}
