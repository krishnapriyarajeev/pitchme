import { useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { VoiceStatus } from '@/components/voice-status';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ConfirmSheet } from '@/components/ui/confirm-sheet';
import { EmptyState } from '@/components/ui/empty-state';
import { Icon } from '@/components/ui/icon';
import { Screen } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { useAuth } from '@/hooks/use-auth';
import { useRefreshOnFocus } from '@/hooks/use-refresh-on-focus';
import { useRequest } from '@/hooks/use-request';
import { useTheme } from '@/hooks/use-theme';
import { getProfile, listSessions, messageOf, type SessionSummary } from '@/lib/api';
import { initialsOf } from '@/lib/format';

/** The most rehearsals the stats count; more show as "100+". */
const COUNT_LIMIT = 100;
const POLL_MS = 5000;

export default function ProfileTab() {
  const theme = useTheme();
  const router = useRouter();
  const { signOut } = useAuth();
  // While a voice clone is made, check again every few seconds.
  const profile = useRequest('profile', getProfile, {
    pollMs: POLL_MS,
    keepPolling: (data) => data?.voice_clone_status === 'pending',
  });
  const sessions = useRequest('sessions:count', () => listSessions(COUNT_LIMIT));
  const [confirming, setConfirming] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  const reloadProfile = profile.reload;
  const reloadSessions = sessions.reload;
  const refresh = useCallback(() => {
    void reloadProfile();
    void reloadSessions();
  }, [reloadProfile, reloadSessions]);
  useRefreshOnFocus(refresh);

  const data = profile.data;
  if (profile.loading) return <Screen edges={['top']}>{null}</Screen>;
  if (!data) {
    return (
      <Screen edges={['top']} contentStyle={styles.centre}>
        <EmptyState
          icon="info"
          title="Your profile did not load"
          body={messageOf(profile.error)}
          action={{ label: 'Try again', onPress: refresh }}
        />
      </Screen>
    );
  }

  return (
    <Screen scroll edges={['top']} contentStyle={styles.content}>
      <Rise style={styles.header}>
        <View style={[styles.avatar, { backgroundColor: theme.accentSoft }]}>
          {initialsOf(data.display_name) ? (
            <Text variant="cardTitle" color="accent" style={styles.initials}>
              {initialsOf(data.display_name)}
            </Text>
          ) : (
            <Icon name="user" size={24} color={theme.accent} />
          )}
        </View>
        <Text variant="title" style={styles.name} accessibilityRole="header">
          {data.display_name || 'Your profile'}
        </Text>
        {data.role_title ? (
          <Text variant="body" color="textSecondary">
            {data.role_title}
          </Text>
        ) : null}
        <Text variant="secondary" color="textSubtle">
          {data.email}
        </Text>
      </Rise>

      <Rise index={1} style={styles.stats}>
        <Stat label="REHEARSALS" value={countText(sessions.data)} detail="in total" />
        <Stat label="THIS MONTH" value={countText(sessions.data, startOfMonth())} detail="so far" />
      </Rise>

      <Rise index={2} style={styles.section}>
        <Card>
          <View style={styles.cardHead}>
            <Text variant="pill" color="textSubtle">
              WHAT YOU SELL
            </Text>
            <Pressable
              onPress={() => router.push('/profile/edit')}
              accessibilityRole="button"
              accessibilityLabel="Edit your details"
              hitSlop={12}>
              <Text variant="label" color="accent">
                Edit
              </Text>
            </Pressable>
          </View>
          <Text variant="body" color={data.sells ? 'text' : 'textSecondary'} style={styles.sells}>
            {data.sells || 'Not set yet. Add it, and the buyer asks about your real product.'}
          </Text>
        </Card>
      </Rise>

      <Rise index={3} style={styles.section}>
        <VoiceStatus profile={data} reload={profile.reload} />
      </Rise>

      <Rise index={4} style={styles.section}>
        <Pressable
          onPress={() => router.navigate('/playbook')}
          accessibilityRole="button"
          accessibilityLabel="Your playbook">
          <Card style={styles.linkRow}>
            <Icon name="book" size={20} color={theme.textSecondary} />
            <View style={styles.linkText}>
              <Text variant="rowTitle">Your playbook</Text>
              <Text variant="secondary" color="textSecondary">
                {data.has_playbook
                  ? 'Added. The debrief checks your answers against it.'
                  : 'Not added yet'}
              </Text>
            </View>
            <Icon name="chevron-right" size={17} color={theme.textSubtle} />
          </Card>
        </Pressable>
      </Rise>

      <Rise index={5} style={styles.section}>
        <Button
          label="Sign out"
          variant="text"
          icon="sign-out"
          onPress={() => setConfirming(true)}
        />
      </Rise>

      <ConfirmSheet
        visible={confirming}
        title="Sign out?"
        body="Your rehearsals, playbook and voice sample stay on your account. Sign in again to get back to them."
        confirmLabel="Sign out"
        cancelLabel="Stay signed in"
        confirming={signingOut}
        onCancel={() => setConfirming(false)}
        onConfirm={async () => {
          setSigningOut(true);
          // The layout moves to the sign-in screen when the state changes.
          await signOut();
        }}
      />
    </Screen>
  );
}

function startOfMonth(now = new Date()): Date {
  return new Date(now.getFullYear(), now.getMonth(), 1);
}

/** A count from the loaded page of sessions, or a dash while it loads. */
function countText(sessions: SessionSummary[] | undefined, since?: Date): string {
  if (!sessions) return '–';
  const count = since
    ? sessions.filter((session) => new Date(session.created_at) >= since).length
    : sessions.length;
  return count >= COUNT_LIMIT ? `${COUNT_LIMIT}+` : String(count);
}

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <Card
      style={styles.stat}
      accessible
      accessibilityLabel={`${value} ${label.toLowerCase()} ${detail}`}>
      <Text variant="pill" color="textSubtle">
        {label}
      </Text>
      <Text variant="numeral" style={styles.statValue}>
        {value}
      </Text>
      <Text variant="secondary" color="textSecondary">
        {detail}
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 12, paddingBottom: 24 },
  centre: { justifyContent: 'center' },
  header: { alignItems: 'center', gap: 2 },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  initials: { fontSize: 20, lineHeight: 24 },
  name: { fontSize: 25, lineHeight: 30, textAlign: 'center' },
  stats: { marginTop: 20, flexDirection: 'row', gap: 8 },
  stat: { flex: 1, alignItems: 'center', paddingVertical: 14 },
  statValue: { marginTop: 3, fontSize: 30, lineHeight: 34 },
  section: { marginTop: 12 },
  cardHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sells: { marginTop: 6 },
  linkRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  linkText: { flex: 1, gap: 1 },
});
