import { apiRequest } from './client';
import type { Lease } from '../types';

function mapLease(raw: any): Lease {
  return {
    id: raw.id,
    propertyId: raw.property_id,
    propertyName: raw.property_name ?? '',
    tenantUserId: raw.tenant_user_id,
    tenantName: raw.tenant_name,
    startDate: typeof raw.start_date === 'string' ? raw.start_date : String(raw.start_date),
    endDate: typeof raw.end_date === 'string' ? raw.end_date : String(raw.end_date),
    rentAmount: raw.rent_amount,
    securityDeposit: raw.security_deposit,
    status: raw.status,
  };
}

export async function getLeases(): Promise<Lease[]> {
  const data = await apiRequest<any[]>('/leases');
  return data.map(mapLease);
}

export async function getLease(id: string): Promise<Lease> {
  const raw = await apiRequest<any>(`/leases/${id}`);
  return mapLease(raw);
}
