import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import { useFonts } from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import * as SystemUI from 'expo-system-ui';
import { useEffect } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { FontFiles } from '@/constants/fonts';
import { AuthProvider, useAuth } from '@/hooks/use-auth';
import { useScheme, useTheme } from '@/hooks/use-theme';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AuthProvider>
          <RootStack />
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

function RootStack() {
  const scheme = useScheme();
  const theme = useTheme();
  const { status, onboarding } = useAuth();
  // A font that fails to load falls back to the system font; the app still
  // opens rather than staying on the splash screen.
  const [fontsLoaded, fontError] = useFonts(FontFiles);
  const ready = (fontsLoaded || fontError !== null) && status !== 'checking';
  const signedIn = status === 'signed_in';

  useEffect(() => {
    if (ready) SplashScreen.hideAsync();
  }, [ready]);

  useEffect(() => {
    // The native view behind the navigator is white by default, and it shows
    // between two screens during a transition.
    SystemUI.setBackgroundColorAsync(theme.background);
  }, [theme.background]);

  // The splash screen stays up while the saved sign-in is checked, so a
  // returning user never sees the landing screen flash past.
  if (!ready) return null;

  // The navigator paints its own background during a transition too.
  const base = scheme === 'dark' ? DarkTheme : DefaultTheme;
  const navigationTheme = {
    ...base,
    colors: {
      ...base.colors,
      background: theme.background,
      card: theme.surface,
      text: theme.text,
      border: theme.border,
      primary: theme.accent,
    },
  };

  // Screens are shown by sign-in state. When the state changes, the user
  // moves to the first screen they may now see, in the order below: a new
  // account to onboarding, a sign-in to Home, a sign-out to sign in.
  return (
    <ThemeProvider value={navigationTheme}>
      <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
      <Stack
        screenOptions={{
          headerShown: false,
          animation: 'slide_from_right',
          contentStyle: { backgroundColor: theme.background },
        }}>
        <Stack.Protected guard={signedIn && onboarding}>
          <Stack.Screen name="onboard/voice" />
          <Stack.Screen name="onboard/playbook" />
        </Stack.Protected>
        <Stack.Protected guard={signedIn}>
          <Stack.Screen name="(tabs)" options={{ animation: 'fade' }} />
          <Stack.Screen name="profile/edit" />
          <Stack.Screen name="profile/voice" />
          <Stack.Screen name="sessions" />
        </Stack.Protected>
        <Stack.Protected guard={!signedIn}>
          <Stack.Screen name="login" options={{ animation: 'fade' }} />
          <Stack.Screen name="index" options={{ animation: 'fade' }} />
          <Stack.Screen name="onboard/index" />
        </Stack.Protected>
      </Stack>
    </ThemeProvider>
  );
}
