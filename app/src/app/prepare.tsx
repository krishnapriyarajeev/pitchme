import { useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, View, type TextInput } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { Screen, ScreenHeader } from '@/components/ui/screen';
import { SelectField } from '@/components/ui/select-field';
import { Text } from '@/components/ui/text';
import { TextField } from '@/components/ui/text-field';
import {
  AUDIENCES,
  COMPOSURES,
  DEAL_STAGES,
  INDUSTRIES,
  type Audience,
  type Composure,
  type DealStage,
} from '@/constants/deal';
import { useTheme } from '@/hooks/use-theme';
import { createSession } from '@/lib/api';
import { keepCall } from '@/lib/call-store';
import { formError, type FieldErrors } from '@/lib/forms';

const INDUSTRY_CHOICES = INDUSTRIES.map((name) => ({ key: name, label: name }));
const FIELDS = ['prospect_name', 'company', 'industry', 'deal_stage', 'competitors'] as const;

/** The deal. Every answer changes how the AI buyer acts. */
export default function Prepare() {
  const theme = useTheme();
  const router = useRouter();
  const companyRef = useRef<TextInput>(null);

  const [prospect, setProspect] = useState('');
  const [company, setCompany] = useState('');
  const [industry, setIndustry] = useState<string | null>(null);
  const [stage, setStage] = useState<DealStage>('discovery');
  const [audience, setAudience] = useState<Audience>('general');
  const [composure, setComposure] = useState<Composure>('direct');
  const [competitors, setCompetitors] = useState('');
  const [busy, setBusy] = useState(false);
  const [fields, setFields] = useState<FieldErrors>({});
  const [message, setMessage] = useState<string | null>(null);

  async function start() {
    if (busy) return;
    const missing: FieldErrors = {};
    if (!prospect.trim()) missing.prospect_name = 'Add who you are meeting.';
    if (!company.trim()) missing.company = 'Add their company.';
    setFields(missing);
    setMessage(null);
    if (Object.keys(missing).length > 0) return;

    setBusy(true);
    try {
      const room = await createSession({
        prospect_name: prospect.trim(),
        company: company.trim(),
        industry: industry ?? undefined,
        deal_stage: stage,
        audience_type: audience,
        buyer_composure: composure,
        competitors: competitors.trim() || undefined,
      });
      keepCall(room, {
        name: prospect.trim(),
        company: company.trim(),
        manner: COMPOSURES.find((c) => c.key === composure)?.hint ?? '',
      });
      router.replace(`/call/${room.session_id}`);
    } catch (error) {
      // Say why the start failed, under the field when it is about one.
      const result = formError(error, FIELDS);
      setFields(result.fields);
      setMessage(result.message);
      setBusy(false);
    }
  }

  return (
    <Screen
      scroll
      keyboardAvoiding
      contentStyle={styles.content}
      footer={
        <Button
          label="Start the rehearsal"
          icon="chevron-right"
          iconTrailing
          loading={busy}
          onPress={start}
        />
      }>
      <ScreenHeader title="New rehearsal" />
      <Rise style={styles.intro}>
        <Text variant="title" accessibilityRole="header">
          Who are you meeting?
        </Text>
        <Text variant="body" color="textSecondary" style={styles.subhead}>
          The buyer&apos;s questions, pushback and priorities come from this.
        </Text>
      </Rise>

      <Rise index={1} style={styles.form}>
        <TextField
          label="Prospect"
          placeholder="Jo Bennett"
          value={prospect}
          onChangeText={setProspect}
          error={fields.prospect_name}
          autoCapitalize="words"
          returnKeyType="next"
          onSubmitEditing={() => companyRef.current?.focus()}
        />
        <TextField
          ref={companyRef}
          label="Company"
          placeholder="Saber Industries"
          value={company}
          onChangeText={setCompany}
          error={fields.company}
          autoCapitalize="words"
        />
        <SelectField
          label="Their role"
          placeholder="Choose a role"
          options={AUDIENCES}
          value={audience}
          onChange={setAudience}
        />
        <SelectField
          label="Deal stage"
          placeholder="Choose a stage"
          options={DEAL_STAGES}
          value={stage}
          onChange={setStage}
        />
        <SelectField
          label="How they push back"
          placeholder="Choose a manner"
          options={COMPOSURES}
          value={composure}
          onChange={setComposure}
        />
        <SelectField
          label="Industry"
          optional
          placeholder="Choose an industry"
          options={INDUSTRY_CHOICES}
          value={industry}
          onChange={setIndustry}
        />
      </Rise>

      <View style={[styles.rule, { backgroundColor: theme.border }]} />

      <Rise index={2}>
        <TextField
          label="Competitors"
          optional
          placeholder="Who else they are talking to"
          value={competitors}
          onChangeText={setCompetitors}
          error={fields.competitors}
          helper="The buyer may compare you with them."
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
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: 24 },
  intro: { marginTop: 12 },
  subhead: { marginTop: 7 },
  form: { marginTop: 20, gap: 14 },
  rule: { height: 1, marginVertical: 20 },
  note: { marginTop: 18 },
});
