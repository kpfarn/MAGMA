interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        width: '100%',
        maxWidth: '800px',
        margin: '0 auto',
      }}
    >
      <div
        style={{
          display: 'flex',
          gap: '12px',
          alignItems: 'flex-start',
          flexDirection: isUser ? 'row-reverse' : 'row',
          width: '100%',
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: isUser
              ? 'rgba(255, 255, 255, 0.2)'
              : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '16px',
            flexShrink: 0,
          }}
        >
          {isUser ? '👤' : '💎'}
        </div>
        <div
          style={{
            flex: 1,
            background: isUser
              ? 'rgba(255, 255, 255, 0.1)'
              : 'rgba(255, 255, 255, 0.05)',
            borderRadius: '12px',
            padding: '16px',
            border: `1px solid ${isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.1)'}`,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            lineHeight: '1.6',
            fontSize: '15px',
          }}
        >
          {message.content}
        </div>
      </div>
    </div>
  );
}

