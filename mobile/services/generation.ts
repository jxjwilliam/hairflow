import api from './api';
import { GenerateResult } from '../types';

export async function generateHairstyle(
  photoBase64: string,
  styleId: string,
): Promise<GenerateResult> {
  const res = await api.post('/api/generate', {
    photo_base64: photoBase64,
    style_id: styleId,
  });
  return res.data;
}
