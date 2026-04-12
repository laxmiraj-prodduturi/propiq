import { apiRequest } from './client';
import type { MaintenanceRequest } from '../types';

function mapRequest(raw: any): MaintenanceRequest {
  return {
    id: raw.id,
    propertyId: raw.property_id,
    tenantUserId: raw.tenant_user_id,
    propertyName: raw.property_name,
    tenantName: raw.tenant_name,
    category: raw.category,
    description: raw.description,
    urgency: raw.urgency,
    status: raw.status,
    assignedVendor: raw.assigned_vendor ?? null,
    estimatedCost: raw.estimated_cost ?? null,
    createdAt: raw.created_at,
    resolvedAt: raw.resolved_at ?? null,
  };
}

export async function getMaintenanceRequests(): Promise<MaintenanceRequest[]> {
  const data = await apiRequest<any[]>('/maintenance/requests');
  return data.map(mapRequest);
}

export async function getMaintenanceRequest(id: string): Promise<MaintenanceRequest> {
  const raw = await apiRequest<any>(`/maintenance/requests/${id}`);
  return mapRequest(raw);
}

export async function createMaintenanceRequest(payload: {
  property_id: string;
  property_name: string;
  tenant_name: string;
  category: string;
  description: string;
  urgency: string;
}): Promise<MaintenanceRequest> {
  const raw = await apiRequest<any>('/maintenance/requests', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return mapRequest(raw);
}

export async function updateMaintenanceStatus(
  id: string,
  status: string,
  assignedVendor?: string,
  estimatedCost?: number
): Promise<MaintenanceRequest> {
  const raw = await apiRequest<any>(`/maintenance/requests/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status, assigned_vendor: assignedVendor, estimated_cost: estimatedCost }),
  });
  return mapRequest(raw);
}
