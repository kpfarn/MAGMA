'use client';

import { useState, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = () => {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        gap: '12px',
        alignItems: 'flex-end',
        maxWidth: '800px',
        margin: '0 auto',
        width: '100%',
      }}
    >
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask MAGMA about stocks, your portfolio, or market news..."
        disabled={disabled}
        style={{
          flex: 1,
          background: 'rgba(255, 255, 255, 0.05)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          borderRadius: '12px',
          padding: '12px 16px',
          color: '#ececf1',
          fontSize: '15px',
          resize: 'none',
          minHeight: '52px',
          maxHeight: '200px',
          fontFamily: 'inherit',
          outline: 'none',
          opacity: disabled ? 0.5 : 1,
          cursor: disabled ? 'not-allowed' : 'text',
        }}
        rows={1}
        onInput={(e) => {
          const target = e.target as HTMLTextAreaElement;
          target.style.height = 'auto';
          target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
        }}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !input.trim()}
        style={{
          padding: '12px 24px',
          background: disabled || !input.trim()
            ? 'rgba(255, 255, 255, 0.1)'
            : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          border: 'none',
          borderRadius: '12px',
          color: '#ececf1',
          fontSize: '15px',
          fontWeight: 500,
          cursor: disabled || !input.trim() ? 'not-allowed' : 'pointer',
          opacity: disabled || !input.trim() ? 0.5 : 1,
          transition: 'opacity 0.2s',
          height: '52px',
        }}
      >
        Send
      </button>
    </div>
  );
}

