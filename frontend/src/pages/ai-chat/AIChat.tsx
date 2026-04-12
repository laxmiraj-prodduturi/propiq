import { useEffect, useRef, useState } from 'react';
import { approveAIAction, getAIChatHistory, resumeAIAction, sendAIChatMessage } from '../../api/ai';
import { useAuth } from '../../context/AuthContext';
import type { AIMessage, ActionCard } from '../../types';

const SUGGESTIONS: Record<string, string[]> = {
  owner: [
    'Generate my monthly report',
    'Summarize open maintenance requiring approval',
    'Show me overdue payments',
  ],
  manager: [
    'Triage maintenance requests',
    'Which leases are expiring soon?',
    'Show me overdue payments',
  ],
  tenant: [
    'When is my next rent due?',
    'What does my lease say about pets?',
    'Help me with a maintenance issue',
  ],
};

function buildWelcomeMessage(): AIMessage {
  return {
    id: 'welcome',
    role: 'assistant',
    content: 'Ask about maintenance, leases, payments, or owner reporting.',
    createdAt: new Date().toISOString(),
  };
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export default function AIChat() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<AIMessage[]>([buildWelcomeMessage()]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const messagesEnd = useRef<HTMLDivElement>(null);

  const suggestions = SUGGESTIONS[user?.role ?? 'tenant'];

  useEffect(() => {
    getAIChatHistory()
      .then(({ sessionId: nextSessionId, messages: history }) => {
        if (nextSessionId) {
          setSessionId(nextSessionId);
        }
        if (history.length > 0) {
          setMessages(history);
        }
      })
      .catch(() => {
        setMessages([buildWelcomeMessage()]);
      });
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || submitting) {
      return;
    }

    const userMessage: AIMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content: trimmed,
      createdAt: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setSubmitting(true);

    try {
      const response = await sendAIChatMessage(trimmed, sessionId ?? undefined);
      setSessionId(response.sessionId);
      setMessages(prev => [...prev, response.message]);
    } catch {
      setMessages(prev => [
        ...prev,
        {
          id: `fallback-${Date.now()}`,
          role: 'assistant',
          content: 'AI service is unavailable right now. Try again after the backend is running.',
          createdAt: new Date().toISOString(),
        },
      ]);
    } finally {
      setSubmitting(false);
    }
  };

  const handleActionCard = async (card: ActionCard, approved: boolean) => {
    // Optimistically update the action card status
    setMessages(prev =>
      prev.map(message =>
        message.actionCard?.actionId === card.actionId
          ? { ...message, actionCard: { ...message.actionCard, status: approved ? 'approved' : 'rejected' } }
          : message
      )
    );

    try {
      await approveAIAction(card.actionId, approved);

      if (approved) {
        // Resume the paused LangGraph to get the agent's follow-up response
        const resume = await resumeAIAction(card.actionId);
        setMessages(prev => [...prev, resume.message]);
      } else {
        setMessages(prev => [
          ...prev,
          {
            id: `rejection-${Date.now()}`,
            role: 'assistant',
            content: 'The action has been rejected. No changes will be made.',
            createdAt: new Date().toISOString(),
          },
        ]);
      }
    } catch {
      setMessages(prev => [
        ...prev,
        {
          id: `approval-error-${Date.now()}`,
          role: 'assistant',
          content: 'Could not process the approval. Please try again.',
          createdAt: new Date().toISOString(),
        },
      ]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void sendMessage(input);
    }
  };

  return (
    <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="page-header" style={{ marginBottom: 0 }}>
        <div>
          <h2>AI Assistant</h2>
          <p>Backend-connected assistant with approval actions</p>
        </div>
      </div>

      {suggestions.length > 0 && messages.length <= 1 && (
        <div className="chat-suggestions" style={{ marginTop: 16 }}>
          {suggestions.map(suggestion => (
            <button key={suggestion} className="chat-suggestion" onClick={() => void sendMessage(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>
      )}

      <div className="chat-container" style={{ marginTop: 16 }}>
        <div className="chat-messages">
          {messages.map(msg => (
            <div key={msg.id} className={`chat-message ${msg.role === 'user' ? 'user' : ''}`}>
              <div className={`chat-avatar ${msg.role === 'user' ? 'user-avatar' : 'ai'}`}>
                {msg.role === 'user' ? (user?.avatarInitials ?? 'U') : 'Q'}
              </div>
              <div>
                <div className={`chat-bubble ${msg.role === 'user' ? 'user' : 'ai'}`}>
                  <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                  {formatTime(msg.createdAt)}
                </div>
                {msg.actionCard && (
                  <div className="action-card">
                    <div className="action-card-title">Approval Required</div>
                    <div style={{ fontWeight: 700, fontSize: 13.5, color: 'var(--text-primary)', marginBottom: 4 }}>
                      {msg.actionCard.title}
                    </div>
                    <div className="action-card-desc">{msg.actionCard.description}</div>
                    {msg.actionCard.status === 'pending' ? (
                      <div className="action-card-actions">
                        <button className="btn btn-success btn-sm" onClick={() => void handleActionCard(msg.actionCard!, true)}>
                          Approve
                        </button>
                        <button className="btn btn-danger btn-sm" onClick={() => void handleActionCard(msg.actionCard!, false)}>
                          Reject
                        </button>
                      </div>
                    ) : (
                      <span className={`badge ${msg.actionCard.status === 'approved' ? 'badge-success' : 'badge-danger'}`}>
                        {msg.actionCard.status}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEnd} />
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <textarea
          className="form-input"
          rows={3}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about maintenance, leases, payments, or reports..."
          style={{ resize: 'vertical' }}
        />
        <div className="flex gap-2 justify-end mt-3">
          <button className="btn btn-primary" disabled={submitting || !input.trim()} onClick={() => void sendMessage(input)}>
            {submitting ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
