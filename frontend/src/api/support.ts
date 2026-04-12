import { apiRequest } from './client';

export interface SupportMessage {
  role: 'user' | 'assistant';
  content: string;
}

export async function sendSupportMessage(
  message: string,
  history: SupportMessage[],
): Promise<string> {
  const data = await apiRequest<{ response: string }>('/ai/support/chat', {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  });
  return data.response;
}
