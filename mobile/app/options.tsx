import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import Slider from '@react-native-community/slider';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { colors, spacing, radii } from '../constants/theme';
import type { GenerationOptions } from '../types';

type PipelineOption = GenerationOptions['pipeline'];
type MethodOption = GenerationOptions['method'];

const PIPELINES: { value: PipelineOption; label: string; desc: string }[] = [
  { value: 'photomaker', label: 'PhotoMaker v1', desc: 'SD1.5 保持人脸特征，生成最自然' },
  { value: 'sd15', label: 'Realistic Vision', desc: 'SD1.5 真实风格，脸型可能变化' },
  { value: 'flux', label: 'FLUX.1 Schnell', desc: '最快生成，风格化效果' },
  { value: 'flux_klein', label: 'FLUX.2 Klein 4B', desc: '最新模型，细节丰富' },
];

const METHODS: { value: MethodOption; label: string; desc: string }[] = [
  { value: 'photomaker', label: '保持人脸', desc: '保留您的面部特征（推荐）' },
  { value: 'txt2img', label: '文本生成', desc: '仅根据提示词生成，不依赖原图' },
  { value: 'img2img', label: '图生图', desc: '在原图基础上变换发型' },
];

export default function OptionsScreen() {
  const { templateId, templateName, photoBase64 } = useLocalSearchParams<{
    templateId: string;
    templateName?: string;
    photoBase64: string;
  }>();
  const router = useRouter();

  const [pipeline, setPipeline] = useState<PipelineOption>('photomaker');
  const [method, setMethod] = useState<MethodOption>('photomaker');
  const [denoise, setDenoise] = useState(0.85);
  const [steps, setSteps] = useState(25);

  const selectedPipeline = PIPELINES.find((p) => p.value === pipeline);

  const canUsePhotoMaker = pipeline === 'photomaker';
  const resolvedMethod: MethodOption = canUsePhotoMaker ? 'photomaker' : method;

  const handleStart = () => {
    const options: GenerationOptions = {
      pipeline,
      method: resolvedMethod,
      denoise: resolvedMethod === 'photomaker' || resolvedMethod === 'img2img' ? denoise : 1.0,
      steps,
      cfg: pipeline.startsWith('flux') ? 1.0 : 6.5,
    };
    router.replace({
      pathname: '/preview',
      params: {
        templateId,
        templateName: templateName ?? '',
        photoBase64,
        generationOptions: JSON.stringify(options),
      },
    });
  };

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.title}>生成选项</Text>
        <Text style={styles.subtitle}>
          {templateName ? `发型：${templateName}` : '选择生成参数'}
        </Text>

        {/* Pipeline selection */}
        <Text style={styles.sectionLabel}>模型</Text>
        {PIPELINES.map((p) => (
          <TouchableOpacity
            key={p.value}
            style={[
              styles.optionCard,
              pipeline === p.value && styles.optionCardActive,
            ]}
            onPress={() => {
              setPipeline(p.value);
              if (p.value !== 'photomaker') {
                setMethod('img2img');
              }
            }}
            accessibilityRole="button"
            accessibilityLabel={p.label}
          >
            <View style={styles.optionHeader}>
              <View
                style={[
                  styles.radio,
                  pipeline === p.value && styles.radioActive,
                ]}
              >
                {pipeline === p.value && <View style={styles.radioDot} />}
              </View>
              <Text
                style={[
                  styles.optionLabel,
                  pipeline === p.value && styles.optionLabelActive,
                ]}
              >
                {p.label}
              </Text>
            </View>
            <Text style={styles.optionDesc}>{p.desc}</Text>
          </TouchableOpacity>
        ))}

        {/* Method selection (hidden for photomaker) */}
        {!canUsePhotoMaker && (
          <>
            <Text style={styles.sectionLabel}>生成方式</Text>
            {METHODS.filter((m) => m.value !== 'photomaker').map((m) => (
              <TouchableOpacity
                key={m.value}
                style={[
                  styles.optionCard,
                  method === m.value && styles.optionCardActive,
                ]}
                onPress={() => setMethod(m.value)}
                accessibilityRole="button"
                accessibilityLabel={m.label}
              >
                <View style={styles.optionHeader}>
                  <View
                    style={[
                      styles.radio,
                      method === m.value && styles.radioActive,
                    ]}
                  >
                    {method === m.value && <View style={styles.radioDot} />}
                  </View>
                  <Text
                    style={[
                      styles.optionLabel,
                      method === m.value && styles.optionLabelActive,
                    ]}
                  >
                    {m.label}
                  </Text>
                </View>
                <Text style={styles.optionDesc}>{m.desc}</Text>
              </TouchableOpacity>
            ))}
          </>
        )}

        {/* Denoise slider (img2img only) */}
        {(resolvedMethod === 'img2img' || resolvedMethod === 'photomaker') && (
          <>
            <Text style={styles.sectionLabel}>
              变化程度: {Math.round(denoise * 100)}%
            </Text>
            <View style={styles.sliderRow}>
              <Text style={styles.sliderEnd}>保守</Text>
              <Slider
                style={styles.slider}
                minimumValue={0.5}
                maximumValue={1.0}
                step={0.05}
                value={denoise}
                onValueChange={setDenoise}
                minimumTrackTintColor={colors.primary}
                maximumTrackTintColor={colors.border}
                thumbTintColor={colors.primary}
              />
              <Text style={styles.sliderEnd}>大胆</Text>
            </View>
          </>
        )}

        {/* Steps (flux needs fewer) */}
        <Text style={styles.sectionLabel}>
          生成步数: {steps}
        </Text>
        <View style={styles.sliderRow}>
          <Text style={styles.sliderEnd}>快</Text>
          <Slider
            style={styles.slider}
            minimumValue={pipeline.startsWith('flux') ? 2 : 15}
            maximumValue={pipeline.startsWith('flux') ? 8 : 50}
            step={1}
            value={steps}
            onValueChange={setSteps}
            minimumTrackTintColor={colors.primary}
            maximumTrackTintColor={colors.border}
            thumbTintColor={colors.primary}
          />
          <Text style={styles.sliderEnd}>精细</Text>
        </View>

        {/* Summary */}
        <View style={styles.summaryBox}>
          <Text style={styles.summaryTitle}>即将生成</Text>
          <Text style={styles.summaryText}>
            模型: {selectedPipeline?.label}{'\n'}
            方式: {METHODS.find((m) => m.value === resolvedMethod)?.label}{'\n'}
            {resolvedMethod === 'photomaker' || resolvedMethod === 'img2img'
              ? `变化程度: ${Math.round(denoise * 100)}%\n`
              : ''}
            步数: {steps}
            {pipeline.startsWith('flux') ? '\nCFG: 1.0 (FLUX 固定)' : ''}
          </Text>
        </View>

        {/* Actions */}
        <TouchableOpacity
          style={styles.startBtn}
          onPress={handleStart}
          accessibilityRole="button"
          accessibilityLabel="开始生成"
        >
          <Text style={styles.startBtnText}>开始生成</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.backBtn}
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel="返回拍照"
        >
          <Text style={styles.backBtnText}>返回重拍</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  scroll: {
    flexGrow: 1,
    padding: spacing.lg,
    paddingBottom: spacing.xxl * 2,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: spacing.xl,
  },
  sectionLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  optionCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1.5,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  optionCardActive: {
    borderColor: colors.primary,
    backgroundColor: colors.primarySoft,
  },
  optionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.textMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioActive: {
    borderColor: colors.primary,
  },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary,
  },
  optionLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.text,
  },
  optionLabelActive: {
    color: colors.primary,
  },
  optionDesc: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    marginLeft: 28,
  },
  sliderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.xs,
  },
  slider: {
    flex: 1,
    height: 40,
  },
  sliderEnd: {
    fontSize: 12,
    color: colors.textMuted,
    width: 40,
    textAlign: 'center',
  },
  summaryBox: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginTop: spacing.xl,
  },
  summaryTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  summaryText: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 20,
  },
  startBtn: {
    backgroundColor: colors.primary,
    borderRadius: radii.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: spacing.xl,
  },
  startBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  backBtn: {
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  backBtnText: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: '500',
  },
});
