import { useRef, useState } from 'react';
import { StyleSheet, View, type TextInput } from 'react-native';

import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { EmptyState } from '@/components/ui/empty-state';
import { Screen, ScreenHeader } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { TextField } from '@/components/ui/text-field';
import { useGoBack } from '@/hooks/use-go-back';
import { useRequest } from '@/hooks/use-request';
import { getProfile, messageOf, updateProfile, type Profile } from '@/lib/api';
import { formError, type FieldErrors } from '@/lib/forms';

const FIELDS = ['display_name', 'role_title', 'sells'] as const;

/** The onboarding questions, to answer again at any time. */
export default function EditProfile() {
  const profile = useRequest('profile', getProfile);

  if (profile.loading) return <Screen>{null}</Screen>;
  if (!profile.data) {
    return (
      <Screen>
        <ScreenHeader title="Your details" />
        <EmptyState
          icon="info"
          title="Your details did not load"
          body={messageOf(profile.error)}
          action={{ label: 'Try again', onPress: profile.reload }}
        />
      </Screen>
    );
  }
  // The form starts from the loaded values and then owns them, so a later
  // reload cannot overwrite what the user is typing.
  return <EditForm profile={profile.data} />;
}

function EditForm({ profile }: { profile: Profile }) {
  const goBack = useGoBack('/profile');
  const roleRef = useRef<TextInput>(null);
  const sellsRef = useRef<TextInput>(null);
  const [name, setName] = useState(profile.display_name ?? '');
  const [role, setRole] = useState(profile.role_title ?? '');
  const [sells, setSells] = useState(profile.sells ?? '');
  const [busy, setBusy] = useState(false);
  const [fields, setFields] = useState<FieldErrors>({});
  const [message, setMessage] = useState<string | null>(null);

  async function save() {
    if (busy) return;
    if (!name.trim()) {
      setFields({ display_name: 'Add the name the buyer should call you.' });
      return;
    }
    setBusy(true);
    setFields({});
    setMessage(null);
    try {
      await updateProfile({
        display_name: name.trim(),
        role_title: role.trim(),
        sells: sells.trim(),
      });
      goBack();
    } catch (error) {
      const result = formError(error, FIELDS);
      setFields(result.fields);
      setMessage(result.message && `${result.message} Your changes are still here.`);
      setBusy(false);
    }
  }

  return (
    <Screen scroll keyboardAvoiding footer={<Button label="Save" loading={busy} onPress={save} />}>
      <ScreenHeader title="Your details" />

      {message ? (
        <View style={styles.block}>
          <Callout tone="attention" icon="info">
            <Text variant="secondary" accessibilityLiveRegion="polite">
              {message}
            </Text>
          </Callout>
        </View>
      ) : null}

      <View style={[styles.block, styles.form]}>
        <TextField
          label="What should the buyer call you?"
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
          error={fields.role_title}
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
          error={fields.sells}
          multiline
          helper="The buyer is built from this, and the debrief checks your pitch against it."
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  block: { marginTop: 18 },
  form: { gap: 16 },
});
