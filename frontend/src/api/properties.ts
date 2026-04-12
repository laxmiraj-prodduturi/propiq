import { apiRequest } from './client';
import type { Property } from '../types';

function mapProperty(raw: any): Property {
  return {
    id: raw.id,
    tenantId: raw.tenant_id,
    ownerId: raw.owner_id,
    name: raw.name,
    address: raw.address,
    city: raw.city,
    state: raw.state,
    zip: raw.zip,
    propertyType: raw.property_type,
    bedrooms: raw.bedrooms,
    bathrooms: raw.bathrooms,
    sqft: raw.sqft,
    status: raw.status,
    rentAmount: raw.rent_amount,
    imageColor: raw.image_color,
  };
}

export async function getProperties(): Promise<Property[]> {
  const data = await apiRequest<any[]>('/properties');
  return data.map(mapProperty);
}

export async function getProperty(id: string): Promise<Property> {
  const raw = await apiRequest<any>(`/properties/${id}`);
  return mapProperty(raw);
}

export async function createProperty(payload: {
  name: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  property_type: string;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  status: string;
  rent_amount: number;
  image_color: string;
}): Promise<Property> {
  const raw = await apiRequest<any>('/properties', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return mapProperty(raw);
}
