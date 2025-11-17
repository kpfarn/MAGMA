'use client';

import { useState, useRef, useEffect } from 'react';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import Sidebar from './components/Sidebar';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Determine which endpoint to call based on message content
      let endpoint = '/api/backend/recommendations';
      if (content.toLowerCase().includes('portfolio') || content.toLowerCase().includes('holdings')) {
        endpoint = '/api/backend/portfolio';
      } else if (content.toLowerCase().includes('news')) {
        endpoint = '/api/backend/news';
      }

      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      let assistantContent = '';
      if (data.text) {
        assistantContent = data.text;
      } else if (data.holdings) {
        assistantContent = `Portfolio Summary:\nTotal Value: $${data.summary?.total_value?.toFixed(2) || '0.00'}\nTotal PnL: $${data.summary?.total_pnl?.toFixed(2) || '0.00'}\n\nHoldings:\n${data.holdings.map((h: any) => `- ${h.ticker}: ${h.shares} shares @ $${h.avg_cost?.toFixed(2)} (Current: $${h.last?.toFixed(2)})`).join('\n')}`;
      } else if (data.news) {
        assistantContent = `Recent News:\n\n${data.news.slice(0, 5).map((n: any, i: number) => `${i + 1}. ${n.title}\n   ${n.url}`).join('\n\n')}`;
      } else {
        assistantContent = JSON.stringify(data, null, 2);
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to get response'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickAction = (action: string) => {
    const quickMessages: Record<string, string> = {
      recommendations: 'What are your recommendations for today?',
      portfolio: 'Show me my portfolio summary',
      news: 'What is the latest market news?',
    };
    handleSendMessage(quickMessages[action] || action);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onQuickAction={handleQuickAction}
      />
      
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
        {/* Header */}
        <header
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            background: 'rgba(15, 15, 35, 0.8)',
            backdropFilter: 'blur(10px)',
            zIndex: 10,
          }}
        >
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{
              background: 'transparent',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '6px',
              padding: '8px 12px',
              color: '#ececf1',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            ☰
          </button>
          <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>MAGMA</h1>
          <span style={{ fontSize: '12px', opacity: 0.6, marginLeft: 'auto' }}>
            Market Advisor for Gains using Machine Algorithms
          </span>
        </header>

        {/* Messages Container */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
          }}
        >
          {messages.length === 0 && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                gap: '16px',
                opacity: 0.6,
              }}
            >
              <div style={{ fontSize: '48px' }}>💎</div>
              <h2 style={{ fontSize: '24px', fontWeight: 600 }}>Welcome to MAGMA</h2>
              <p style={{ fontSize: '14px', textAlign: 'center', maxWidth: '500px' }}>
                Ask me about stock recommendations, your portfolio, or market news.
              </p>
              <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap', justifyContent: 'center' }}>
                <button
                  onClick={() => handleQuickAction('recommendations')}
                  style={{
                    padding: '8px 16px',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '8px',
                    color: '#ececf1',
                    cursor: 'pointer',
                    fontSize: '14px',
                  }}
                >
                  Get Recommendations
                </button>
                <button
                  onClick={() => handleQuickAction('portfolio')}
                  style={{
                    padding: '8px 16px',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '8px',
                    color: '#ececf1',
                    cursor: 'pointer',
                    fontSize: '14px',
                  }}
                >
                  View Portfolio
                </button>
                <button
                  onClick={() => handleQuickAction('news')}
                  style={{
                    padding: '8px 16px',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '8px',
                    color: '#ececf1',
                    cursor: 'pointer',
                    fontSize: '14px',
                  }}
                >
                  Latest News
                </button>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {isLoading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '16px',
                background: 'rgba(255, 255, 255, 0.05)',
                borderRadius: '12px',
                maxWidth: '800px',
                margin: '0 auto',
                width: '100%',
              }}
            >
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: '#ececf1',
                  animation: 'pulse 1.5s ease-in-out infinite',
                }}
              />
              <span style={{ fontSize: '14px', opacity: 0.7 }}>MAGMA is thinking...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Container */}
        <div
          style={{
            padding: '16px',
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            background: 'rgba(15, 15, 35, 0.8)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <ChatInput onSend={handleSendMessage} disabled={isLoading} />
        </div>
      </div>

      <style jsx>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }
      `}</style>
    </div>
  );
}

