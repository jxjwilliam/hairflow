import AsyncStorage from '@react-native-async-storage/async-storage';

const HISTORY_KEY = 'hairstyle.generationHistory.v1';
const MAX_ITEMS = 60;

export interface HistoryItem {
  id: string;
  imageUrl: string;
  templateId: string;
  templateName: string;
  createdAt: number;
}

export async function loadHistory(): Promise<HistoryItem[]> {
  try {
    const raw = await AsyncStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as HistoryItem[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function addHistoryItem(
  item: Omit<HistoryItem, 'id' | 'createdAt'> & { id?: string },
): Promise<HistoryItem[]> {
  const next: HistoryItem = {
    id: item.id ?? `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    imageUrl: item.imageUrl,
    templateId: item.templateId,
    templateName: item.templateName,
    createdAt: Date.now(),
  };
  const prev = await loadHistory();
  const merged = [next, ...prev.filter((h) => h.imageUrl !== next.imageUrl)].slice(0, MAX_ITEMS);
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(merged));
  return merged;
}

export async function clearHistory(): Promise<void> {
  await AsyncStorage.removeItem(HISTORY_KEY);
}

export async function removeHistoryItem(id: string): Promise<HistoryItem[]> {
  const prev = await loadHistory();
  const merged = prev.filter((h) => h.id !== id);
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(merged));
  return merged;
}
