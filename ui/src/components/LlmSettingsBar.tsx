import { LlmOpenAiForm, type LlmOpenAiFormProps } from '@/components/LlmOpenAiForm';

type LegacyProps = Omit<LlmOpenAiFormProps, 'surface'> & {
  onDarkBackground?: boolean;
};

/** Thin wrapper for legacy `onDarkBackground` prop */
export function LlmSettingsBar({ onDarkBackground, ...rest }: LegacyProps) {
  return <LlmOpenAiForm {...rest} surface={onDarkBackground ? 'carousel' : 'panel'} />;
}
