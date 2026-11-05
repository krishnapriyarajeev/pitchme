import { EmptyState } from '@/components/ui/empty-state';
import { Screen, ScreenHeader } from '@/components/ui/screen';

export default function ProfileTab() {
  return (
    <Screen scroll edges={['top']}>
      <ScreenHeader title="Profile" leading="none" />
      <EmptyState
        icon="user"
        title="Your profile"
        body="Your name, your role and your voice sample will show here."
      />
    </Screen>
  );
}
