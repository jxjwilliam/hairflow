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
