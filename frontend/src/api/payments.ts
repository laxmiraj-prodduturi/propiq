import { apiRequest } from './client';
import type { Payment } from '../types';

function mapPayment(raw: any): Payment {
  return {
    id: raw.id,
    leaseId: raw.lease_id,
    tenantName: raw.tenant_name,
    propertyName: raw.property_name,
    amount: raw.amount,
    dueDate: typeof raw.due_date === 'string' ? raw.due_date : String(raw.due_date),
    paidDate: raw.paid_date ? (typeof raw.paid_date === 'string' ? raw.paid_date : String(raw.paid_date)) : null,
    paymentMethod: raw.payment_method ?? '',
    status: raw.status,
    lateFee: raw.late_fee ?? 0,
    transactionRef: raw.transaction_ref ?? '',
  };
}

export async function getPayments(): Promise<Payment[]> {
  const data = await apiRequest<any[]>('/payments');
  return data.map(mapPayment);
}

export async function getPaymentHistory(): Promise<Payment[]> {
  const data = await apiRequest<any[]>('/payments/history');
  return data.map(mapPayment);
}

export async function initiatePayment(payload: {
  lease_id: string;
  amount: number;
  payment_method: string;
  due_date: string;
}): Promise<Payment> {
  const raw = await apiRequest<any>('/payments/initiate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return mapPayment(raw);
}
