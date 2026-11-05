import { useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, View, type TextInput } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { Screen, ScreenHeader } from '@/components/ui/screen';
import { StepPills } from '@/components/ui/step-pills';
import { Text } from '@/components/ui/text';
import { TextField } from '@/components/ui/text-field';
import { useAuth } from '@/hooks/use-auth';
import { ApiError } from '@/lib/api';
import { checkSignUp, formError, handOverEmail, PASSWORD_MIN, type FieldErrors } from '@/lib/forms';

const FIELDS = ['display_name', 'email', 'password'] as const;

/**
 * Step 1 of 3: who you are, and the account. The account questions sit among
 * the others rather than in front of them: someone who pressed "Get started"
 * agreed to try a rehearsal, not to fill in a sign-up form first.
 */
export default function AboutYou() {
  const router = useRouter();
  const { signUp } = useAuth();
  const roleRef = useRef<TextInput>(null);
  const sellsRef = useRef<TextInput>(null);
  const emailRef = useRef<TextInput>(null);
  const passwordRef = useRef<TextInput>(null);

  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [sells, setSells] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [fields, setFields] = useState<FieldErrors>({});
  const [message, setMessage] = useState<string | null>(null);
  const [emailTaken, setEmailTaken] = useState(false);

  async function submit() {
    if (busy) return;
    const errors = checkSignUp({ name, email, password });
    setFields(errors);
    setMessage(null);
    setEmailTaken(false);
    if (Object.keys(errors).length > 0) return;

    setBusy(true);
    try {
      // On success the layout moves on to the voice step.
      await signUp({ email, password, name, roleTitle: role, sells });
    } catch (error) {
      if (error instanceof ApiError && error.code === 'email_taken') {
        setEmailTaken(true);
        setMessage(`${error.message} Sign in to carry on where you left off.`);
      } else {
        const result = formError(error, FIELDS);
        setFields(result.fields);
        setMessage(result.message);
      }
      setBusy(false);
    }
  }

  return (
    <Screen scroll keyboardAvoiding contentStyle={styles.content}>
      <ScreenHeader />
      <Rise>
        <StepPills step={1} total={3} />
      </Rise>
      <Rise index={1} style={styles.intro}>
        <Text variant="title" accessibilityRole="header">
          A little about you
        </Text>
        <Text variant="body" color="textSecondary" style={styles.subhead}>
          The buyer is set up from this, and the debrief uses it to check your pitch.
        </Text>
      </Rise>

      <Rise index={2} style={styles.form}>
        <TextField
          label="What should the buyer call you?"
          placeholder="Your name"
          value={name}
          onChangeText={setName}
          error={fields.display_name}
          autoCapitalize="words"
          autoComplete="name"
          returnKeyType="next"
          onSubmitEditing={() => roleRef.current?.focus()}
        />
        <TextField
          ref={roleRef}
          label="What is your role?"
          optional
          placeholder="Account executive"
          value={role}
          onChangeText={setRole}
          autoCapitalize="words"
          returnKeyType="next"
          onSubmitEditing={() => sellsRef.current?.focus()}
        />
        <TextField
          ref={sellsRef}
          label="What do you sell?"
          optional
          placeholder="Payroll software for small firms"
          value={sells}
          onChangeText={setSells}
          multiline
          helper="One or two lines. You can change it later in Profile."
        />
        <TextField
          ref={emailRef}
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
          helper={`At least ${PASSWORD_MIN} characters.`}
          secure
          autoCapitalize="none"
          autoComplete="new-password"
          textContentType="newPassword"
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
            {emailTaken ? (
              <Button
                label="Sign in instead"
                variant="quiet"
                style={styles.signIn}
                onPress={() => {
                  handOverEmail(email);
                  router.replace('/login');
                }}
              />
            ) : null}
          </Callout>
        </View>
      ) : null}

      <Rise index={3} style={styles.actions}>
        <Button label="Continue" loading={busy} onPress={submit} />
      </Rise>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 4, paddingBottom: 28 },
  intro: { marginTop: 18 },
  subhead: { marginTop: 8 },
  form: { marginTop: 22, gap: 16 },
  note: { marginTop: 18 },
  signIn: { marginTop: 12, height: 44 },
  actions: { marginTop: 24 },
});
