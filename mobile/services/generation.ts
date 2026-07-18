import api from './api';
import type { GenerateResult, GenerationOptions } from '../types';

export async function generateHairstyle(
  photoBase64: string,
  styleId: string,
  options?: GenerationOptions,
): Promise<GenerateResult> {
  const res = await api.post('/api/comfyui/generate', {
    photo_base64: photoBase64,
    style_id: styleId,
    pipeline: options?.pipeline ?? 'photomaker',
    method: options?.method ?? 'photomaker',
    denoise: options?.denoise ?? 0.85,
    steps: options?.steps ?? 25,
    cfg: options?.cfg ?? 6.5,
  });
  return res.data;
}

export async function regenerateHairstyle(
  photoBase64: string,
  styleId: string,
  params: { length: number; curl: number; color: string },
): Promise<GenerateResult> {
  const res = await api.post('/api/comfyui/regenerate', {
    photo_base64: photoBase64,
    style_id: styleId,
    params,
  });
  return res.data;
}

export async function generateMultiAngle(
  photoBase64: string,
  styleId: string,
  options?: GenerationOptions,
): Promise<{ images: Record<string, { url: string; id: string }> }> {
  const res = await api.post('/api/comfyui/generate-multi', {
    photo_base64: photoBase64,
    style_id: styleId,
    pipeline: options?.pipeline ?? 'photomaker',
    method: options?.method ?? 'photomaker',
    denoise: options?.denoise ?? 0.85,
    steps: options?.steps ?? 25,
    cfg: options?.cfg ?? 6.5,
  });
  return res.data;
}
