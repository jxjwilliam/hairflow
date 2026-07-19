import api from './api';
import type { GenerateResult, GenerationOptions, VideoGenerateResult } from '../types';

// CPU-only: flux_klein img2img takes ~163s, so override the default 60s timeout
const GENERATE_TIMEOUT = 300_000;
const VIDEO_TIMEOUT = 900_000;

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
  }, { timeout: GENERATE_TIMEOUT });
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
  }, { timeout: GENERATE_TIMEOUT });
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
  }, { timeout: GENERATE_TIMEOUT });
  return res.data;
}

export async function generateVideo(params: {
  imageId?: string;
  imageUrl?: string;
  photoBase64?: string;
}): Promise<VideoGenerateResult> {
  const body: Record<string, string> = {};
  if (params.imageId) body.image_id = params.imageId;
  else if (params.imageUrl) body.image_url = params.imageUrl;
  else if (params.photoBase64) body.photo_base64 = params.photoBase64;
  else throw new Error('generateVideo requires imageId, imageUrl, or photoBase64');

  const res = await api.post('/api/comfyui/generate-video', body, {
    timeout: VIDEO_TIMEOUT,
  });
  return res.data;
}
