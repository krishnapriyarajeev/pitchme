import { useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, View, type TextInput } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { Logo } from '@/components/ui/logo';
import { Screen } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { TextField } from '@/components/ui/text-field';
import { useAuth } from '@/hooks/use-auth';
import { checkSignIn, formError, handedOverEmail, type FieldErrors } from '@/lib/forms';

const FIELDS = ['email', 'password'] as const;

export default function Login() {
  const router = useRouter();
  const { signIn, notice, clearNotice } = useAuth();
  const passwordRef = useRef<TextInput>(null);

  const [email, setEmail] = useState(handedOverEmail);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [fields, setFields] = useState<FieldErrors>({});
  const [message, setMessage] = useState<string | null>(null);

  async function submit() {
    if (busy) return;
    const errors = checkSignIn({ email, password });
    setFields(errors);
    setMessage(null);
    clearNotice();
    if (Object.keys(errors).length > 0) return;

    setBusy(true);
    try {
      // On success the sign-in state changes and the layout moves to Home.
      await signIn(email, password);
    } catch (error) {
      const result = formError(error, FIELDS);
      setFields(result.fields);
      setMessage(result.message);
      setBusy(false);
    }
  }

  return (
    <Screen scroll keyboardAvoiding contentStyle={styles.content}>
      <Rise>
        <Logo size={44} />
      </Rise>
      <Rise index={1}>
        <Text variant="title" style={styles.headline} accessibilityRole="header">
          Welcome back
        </Text>
        <Text variant="body" color="textSecondary" style={styles.subhead}>
          Sign in with the email you used to sign up.
        </Text>
      </Rise>

      {notice ? (
        <Rise index={2} style={styles.note}>
          <Callout icon="info">
            <Text variant="secondary">{notice}</Text>
          </Callout>
        </Rise>
      ) : null}

      <Rise index={3} style={styles.form}>
        <TextField
          label="Email"
          placeholder="you@company.com"
          value={email}
          onChangeText={setEmail}
          error={fields.email}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
          textContentType="emailAddress"
          returnKeyType="next"
          onSubmitEditing={() => passwordRef.current?.focus()}
        />
        <TextField
          ref={passwordRef}
          label="Password"
          value={password}
          onChangeText={setPassword}
          error={fields.password}
          secure
          autoCapitalize="none"
          autoComplete="current-password"
          textContentType="password"
          returnKeyType="go"
          onSubmitEditing={submit}
        />
      </Rise>

      {message ? (
        <View style={styles.note}>
          <Callout tone="attention" icon="info">
            <Text variant="secondary" accessibilityLiveRegion="polite">
              {message}
            </Text>
          </Callout>
        </View>
      ) : null}

      <Rise index={4} style={styles.actions}>
        <Button label="Sign in" loading={busy} onPress={submit} />
        <Button
          label="Create an account"
          variant="text"
          disabled={busy}
          onPress={() => {
            clearNotice();
            router.replace('/onboard');
          }}
        />
      </Rise>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 40, flexGrow: 1 },
  headline: { marginTop: 22 },
  subhead: { marginTop: 8 },
  note: { marginTop: 18 },
  form: { marginTop: 26, gap: 16 },
  actions: { marginTop: 26, gap: 4 },
});
