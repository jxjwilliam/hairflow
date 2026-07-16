import api from './api';
import { Template } from '../types';

export async function fetchTemplates(category?: string): Promise<Template[]> {
  const params = category ? { category } : {};
  const res = await api.get('/api/templates', { params });
  return res.data;
}

export async function fetchTemplate(id: string): Promise<Template> {
  const res = await api.get(`/api/templates/${id}`);
  return res.data;
}
