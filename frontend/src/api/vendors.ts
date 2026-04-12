import { apiRequest } from './client';

export interface Vendor {
  id: string;
  tenant_id: string;
  name: string;
  trade: string;
  email: string;
  phone: string;
  rating: number;
  response_time: string;
  is_active: boolean;
  created_at: string;
}

export interface VendorCreate {
  name: string;
  trade: string;
  email?: string;
  phone?: string;
  rating?: number;
  response_time?: string;
}

export interface VendorUpdate {
  name?: string;
  trade?: string;
  email?: string;
  phone?: string;
  rating?: number;
  response_time?: string;
  is_active?: boolean;
}

export function getVendors(): Promise<Vendor[]> {
  return apiRequest<Vendor[]>('/vendors/');
}

export function createVendor(payload: VendorCreate): Promise<Vendor> {
  return apiRequest<Vendor>('/vendors/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateVendor(id: string, payload: VendorUpdate): Promise<Vendor> {
  return apiRequest<Vendor>(`/vendors/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteVendor(id: string): Promise<void> {
  return apiRequest<void>(`/vendors/${id}`, { method: 'DELETE' });
}
