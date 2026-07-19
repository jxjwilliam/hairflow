export interface Template {
  id: string;
  name: string;
  category: string;
  tags: string[];
  face_shapes?: string[];
  style_id: string;
  thumbnail: string;
  description: string;
}

export interface GenerateResult {
  image_url: string;
  image_id: string;
}

export interface VideoGenerateResult {
  video_url: string;
  video_id: string;
  pipeline: string;
  duration_s: number;
}

export interface AngleImages {
  front: { url: string; id: string };
  left: { url: string; id: string };
  right: { url: string; id: string };
  back: { url: string; id: string };
}

export interface MultiAngleResult {
  images: AngleImages;
  template_name: string;
}

export interface RegenerateParams {
  length: number;
  curl: number;
  color: string;
}

export interface GenerationOptions {
  pipeline: 'photomaker' | 'sd15' | 'flux' | 'flux_klein';
  method: 'photomaker' | 'txt2img' | 'img2img';
  denoise: number;
  steps: number;
  cfg: number;
}
