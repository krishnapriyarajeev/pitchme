import { Tabs } from 'expo-router';

import { TabBar } from '@/components/ui/tab-bar';
import { useTheme } from '@/hooks/use-theme';

/** Home, Playbook and Profile. Each tab keeps its state when you switch. */
export default function TabsLayout() {
  const theme = useTheme();

  return (
    <Tabs
      tabBar={(props) => <TabBar {...props} />}
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: theme.background },
      }}>
      <Tabs.Screen name="home" options={{ title: 'Home' }} />
      <Tabs.Screen name="playbook" options={{ title: 'Playbook' }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile' }} />
    </Tabs>
  );
}
