import { EmptyState } from '@/components/ui/empty-state';
import { Screen, ScreenHeader } from '@/components/ui/screen';

export default function HomeTab() {
  return (
    <Screen scroll edges={['top']}>
      <ScreenHeader title="Home" leading="none" />
      <EmptyState
        icon="video"
        title="No rehearsals yet"
        body="Your rehearsals and their debriefs will show here."
      />
    </Screen>
  );
}
