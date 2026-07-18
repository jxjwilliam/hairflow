import api from './api';

export interface TierInfo {
  id: string;
  label: string;
  max_points: number;
  daily_free: number;
  price_discount: number;
  price: number;
}

export interface MembershipStatus {
  tier: string;
  label: string;
  expires_at: string | null;
  daily_left: number;
  points_balance: number;
  max_points: number;
}

export interface UpgradeResult {
  tier: string;
  status: string;
  expires_at: string;
}

export async function fetchTiers(): Promise<TierInfo[]> {
  const res = await api.get('/api/v1/membership/tiers');
  return res.data.tiers;
}

export async function fetchMembershipStatus(): Promise<MembershipStatus> {
  const res = await api.get('/api/v1/membership/my-status');
  return res.data;
}

export async function upgradeMembership(
  tier: string,
  channel = 'mock',
): Promise<UpgradeResult> {
  const res = await api.post('/api/v1/membership/upgrade', { tier, channel });
  return res.data;
}
