import api from './api';

export interface Package {
  id: string;
  name: string;
  points: number;
  price: number;
}

export interface OrderResult {
  order_no: string;
  amount: number;
  points: number;
  status: string;
}

export async function fetchPackages(): Promise<Package[]> {
  const res = await api.get('/api/v1/payment/packages');
  return res.data;
}

export async function createOrder(
  packageId: string,
  channel: string = 'mock',
): Promise<OrderResult> {
  const res = await api.post('/api/v1/payment/order', {
    package_id: packageId,
    channel,
  });
  return res.data;
}

export async function mockPay(orderNo: string): Promise<{
  status: string;
  points_credited: number;
  balance_after: number;
}> {
  const res = await api.post('/api/v1/payment/mock/notify', {
    order_no: orderNo,
  });
  return res.data;
}
