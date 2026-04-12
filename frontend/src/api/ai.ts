import { apiRequest } from './client';
import type { AIMessage } from '../types';

function mapActionCard(raw: any) {
  if (!raw) {
    return undefined;
  }

  return {
    actionId: raw.action_id,
    type: raw.type,
    title: raw.title,
    description: raw.description,
    status: raw.status,
  };
}

function mapMessage(raw: any): AIMessage {
  return {
    id: raw.id,
    role: raw.role,
    content: raw.content,
    createdAt: raw.created_at,
    actionCard: mapActionCard(raw.action_card),
  };
}

export async function getAIChatHistory(sessionId?: string): Promise<{ sessionId: string | null; messages: AIMessage[] }> {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
  const raw = await apiRequest<any>(`/ai/chat/history${query}`);
  return {
    sessionId: raw.session_id ?? null,
    messages: (raw.messages ?? []).map(mapMessage),
  };
}

export async function sendAIChatMessage(message: string, sessionId?: string): Promise<{ sessionId: string; message: AIMessage }> {
  const raw = await apiRequest<any>('/ai/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      session_id: sessionId,
    }),
  });

  return {
    sessionId: raw.session_id,
    message: mapMessage(raw.message),
  };
}

export async function approveAIAction(actionId: string, approved: boolean): Promise<{ actionId: string; status: 'approved' | 'rejected'; message: string }> {
  const raw = await apiRequest<any>(`/ai/approve/${actionId}?approved=${approved}`, {
    method: 'POST',
  });

  return {
    actionId: raw.action_id,
    status: raw.status,
    message: raw.message,
  };
}

export async function resumeAIAction(actionId: string): Promise<{ sessionId: string; message: AIMessage }> {
  const raw = await apiRequest<any>(`/ai/resume/${actionId}`, {
    method: 'POST',
  });

  return {
    sessionId: raw.session_id,
    message: mapMessage(raw.message),
  };
}
