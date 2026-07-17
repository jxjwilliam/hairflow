export interface Template {
  id: string;
  name: string;
  category: string;
  tags: string[];
  style_id: string;
  thumbnail: string;
  description: string;
}

export interface GenerateResult {
  image_url: string;
  image_id: string;
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
