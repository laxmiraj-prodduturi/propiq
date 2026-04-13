import type React from 'react';

export type Role = 'owner' | 'manager' | 'tenant';

export interface User {
  id: string;
  tenantId: string;
  email: string;
  role: Role;
  firstName: string;
  lastName: string;
  phone: string;
  avatarInitials: string;
}

export type PropertyType = 'residential';
export type UnitStatus = 'vacant' | 'occupied' | 'maintenance';
export type LeaseStatus = 'active' | 'expired' | 'terminated';
export type PaymentStatus = 'pending' | 'paid' | 'late' | 'failed';
export type MaintenanceUrgency = 'low' | 'medium' | 'high' | 'emergency';
export type MaintenanceStatus = 'submitted' | 'assigned' | 'in_progress' | 'resolved' | 'closed';
export type DocumentType = 'lease' | 'notice' | 'invoice' | 'policy' | 'other';
export type NotificationType = 'payment' | 'maintenance' | 'lease' | 'ai' | 'system';

export interface Property {
  id: string;
  tenantId: string;
  ownerId: string;
  name: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  propertyType: PropertyType;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  status: UnitStatus;
  rentAmount: number;
  imageColor: string;
}

export interface Lease {
  id: string;
  propertyId: string;
  propertyName: string;
  tenantUserId: string;
  tenantName: string;
  startDate: string;
  endDate: string;
  rentAmount: number;
  securityDeposit: number;
  status: LeaseStatus;
}

export interface Payment {
  id: string;
  leaseId: string;
  tenantName: string;
  propertyName: string;
  amount: number;
  dueDate: string;
  paidDate: string | null;
  paymentMethod: string;
  status: PaymentStatus;
  lateFee: number;
  transactionRef: string;
}

export interface MaintenanceRequest {
  id: string;
  propertyId: string;
  tenantUserId: string;
  propertyName: string;
  tenantName: string;
  category: string;
  description: string;
  urgency: MaintenanceUrgency;
  status: MaintenanceStatus;
  assignedVendor: string | null;
  estimatedCost: number | null;
  createdAt: string;
  resolvedAt: string | null;
}

export interface Document {
  id: string;
  uploadedBy: string;
  documentType: DocumentType;
  fileName: string;
  fileSize: string;
  mimeType: string;
  relatedEntity: string;
  createdAt: string;
}

export interface Notification {
  id: string;
  userId: string;
  type: NotificationType;
  title: string;
  body: string;
  isRead: boolean;
  createdAt: string;
}

export interface AIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  actionCard?: ActionCard;
}

export interface ActionCard {
  actionId: string;
  type: string;
  title: string;
  description: string;
  status: 'pending' | 'approved' | 'rejected';
}

export interface KPICard {
  label: string;
  value: string;
  change: string;
  changeType: 'up' | 'down' | 'neutral';
  icon: React.ReactNode;
  color: string;
}
