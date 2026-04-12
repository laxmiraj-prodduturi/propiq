import { useEffect, useRef, useState } from 'react';
import { sendSupportMessage, type SupportMessage } from '../../api/support';

interface ChatEntry {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

const WELCOME: ChatEntry = {
  id: 'welcome',
  role: 'assistant',
  content: 'Hi! I\'m your support assistant. Ask me anything about the platform — payments, maintenance, leases, or how features work.',
};

export default function SupportChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatEntry[]>([WELCOME]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      inputRef.current?.focus();
    }
  }, [open, messages]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userEntry: ChatEntry = { id: `u-${Date.now()}`, role: 'user', content: trimmed };
    setMessages(prev => [...prev, userEntry]);
    setInput('');
    setLoading(true);

    // Build history for API (exclude welcome message)
    const history: SupportMessage[] = messages
      .filter(m => m.id !== 'welcome')
      .map(m => ({ role: m.role, content: m.content }));

    try {
      const response = await sendSupportMessage(trimmed, history);
      setMessages(prev => [...prev, { id: `a-${Date.now()}`, role: 'assistant', content: response }]);
    } catch {
      setMessages(prev => [
        ...prev,
        { id: `err-${Date.now()}`, role: 'assistant', content: 'Sorry, I\'m unavailable right now. Please try again shortly.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  };

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          position: 'fixed',
          bottom: 28,
          right: 28,
          width: 52,
          height: 52,
          borderRadius: '50%',
          background: open ? 'var(--bg-elevated)' : 'var(--grad-primary)',
          border: open ? '1px solid var(--border-default)' : 'none',
          boxShadow: open ? 'var(--shadow-md)' : 'var(--primary-glow), var(--shadow-lg)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 22,
          cursor: 'pointer',
          zIndex: 1000,
          transition: 'all var(--t-base) var(--ease)',
        }}
        title={open ? 'Close support chat' : 'Open support chat'}
      >
        {open ? '✕' : '💬'}
      </button>

      {/* Chat panel */}
      {open && (
        <div
          style={{
            position: 'fixed',
            bottom: 92,
            right: 28,
            width: 360,
            maxWidth: 'calc(100vw - 56px)',
            height: 480,
            maxHeight: 'calc(100vh - 120px)',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-xl)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            zIndex: 999,
            animation: 'supportSlideUp 180ms var(--ease)',
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: '14px 16px',
              borderBottom: '1px solid var(--border-subtle)',
              background: 'var(--bg-elevated)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              flexShrink: 0,
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                background: 'var(--grad-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 15,
                flexShrink: 0,
              }}
            >
              🤖
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13.5, color: 'var(--text-primary)' }}>Support Assistant</div>
              <div style={{ fontSize: 11, color: 'var(--emerald)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--emerald)', display: 'inline-block' }} />
                Online
              </div>
            </div>
            <button
              onClick={() => setMessages([WELCOME])}
              style={{
                marginLeft: 'auto',
                fontSize: 11,
                color: 'var(--text-muted)',
                padding: '3px 8px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
                background: 'transparent',
                cursor: 'pointer',
              }}
              title="Clear conversation"
            >
              Clear
            </button>
          </div>

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px 14px',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            {messages.map(msg => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                  alignItems: 'flex-end',
                  gap: 8,
                }}
              >
                {msg.role === 'assistant' && (
                  <div
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: '50%',
                      background: 'var(--primary-10)',
                      border: '1px solid var(--primary-20)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 13,
                      flexShrink: 0,
                    }}
                  >
                    🤖
                  </div>
                )}
                <div
                  style={{
                    maxWidth: '78%',
                    padding: '9px 12px',
                    borderRadius: msg.role === 'user'
                      ? 'var(--radius) var(--radius-xs) var(--radius) var(--radius)'
                      : 'var(--radius-xs) var(--radius) var(--radius) var(--radius)',
                    background: msg.role === 'user' ? 'var(--primary)' : 'var(--bg-elevated)',
                    border: msg.role === 'user' ? 'none' : '1px solid var(--border-subtle)',
                    fontSize: 13,
                    lineHeight: 1.5,
                    color: 'var(--text-primary)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
                <div
                  style={{
                    width: 26, height: 26, borderRadius: '50%',
                    background: 'var(--primary-10)', border: '1px solid var(--primary-20)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13,
                  }}
                >
                  🤖
                </div>
                <div
                  style={{
                    padding: '9px 14px',
                    borderRadius: 'var(--radius-xs) var(--radius) var(--radius) var(--radius)',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    {[0, 1, 2].map(i => (
                      <span
                        key={i}
                        style={{
                          width: 6, height: 6, borderRadius: '50%',
                          background: 'var(--primary-light)',
                          animation: `supportDot 1.2s ${i * 0.2}s ease-in-out infinite`,
                          display: 'inline-block',
                        }}
                      />
                    ))}
                  </span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div
            style={{
              padding: '10px 12px',
              borderTop: '1px solid var(--border-subtle)',
              background: 'var(--bg-elevated)',
              flexShrink: 0,
              display: 'flex',
              gap: 8,
              alignItems: 'flex-end',
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question…"
              rows={1}
              style={{
                flex: 1,
                resize: 'none',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: 13,
                padding: '8px 10px',
                fontFamily: 'var(--font)',
                lineHeight: 1.5,
                outline: 'none',
                maxHeight: 80,
                overflowY: 'auto',
              }}
            />
            <button
              onClick={() => void send(input)}
              disabled={!input.trim() || loading}
              style={{
                width: 36,
                height: 36,
                borderRadius: 'var(--radius-sm)',
                background: input.trim() && !loading ? 'var(--primary)' : 'var(--bg-input)',
                border: '1px solid var(--border-default)',
                color: input.trim() && !loading ? '#fff' : 'var(--text-muted)',
                fontSize: 16,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
                flexShrink: 0,
                transition: 'background var(--t-fast) var(--ease)',
              }}
            >
              ↑
            </button>
          </div>
        </div>
      )}
    </>
  );
}
