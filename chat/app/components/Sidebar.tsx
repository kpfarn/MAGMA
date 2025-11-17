'use client';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onQuickAction: (action: string) => void;
}

export default function Sidebar({ isOpen, onClose, onQuickAction }: SidebarProps) {
  return (
    <>
      {isOpen && (
        <div
          onClick={onClose}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 998,
          }}
        />
      )}
      <aside
        style={{
          position: 'fixed',
          top: 0,
          left: isOpen ? 0 : '-300px',
          width: '300px',
          height: '100vh',
          background: 'rgba(15, 15, 35, 0.95)',
          backdropFilter: 'blur(10px)',
          borderRight: '1px solid rgba(255, 255, 255, 0.1)',
          zIndex: 999,
          transition: 'left 0.3s ease',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          overflowY: 'auto',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600 }}>Quick Actions</h2>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#ececf1',
              fontSize: '24px',
              cursor: 'pointer',
              padding: '4px 8px',
            }}
          >
            ×
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <button
            onClick={() => {
              onQuickAction('recommendations');
              onClose();
            }}
            style={{
              padding: '12px 16px',
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '8px',
              color: '#ececf1',
              cursor: 'pointer',
              fontSize: '14px',
              textAlign: 'left',
            }}
          >
            📈 Get Recommendations
          </button>
          <button
            onClick={() => {
              onQuickAction('portfolio');
              onClose();
            }}
            style={{
              padding: '12px 16px',
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '8px',
              color: '#ececf1',
              cursor: 'pointer',
              fontSize: '14px',
              textAlign: 'left',
            }}
          >
            💼 View Portfolio
          </button>
          <button
            onClick={() => {
              onQuickAction('news');
              onClose();
            }}
            style={{
              padding: '12px 16px',
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '8px',
              color: '#ececf1',
              cursor: 'pointer',
              fontSize: '14px',
              textAlign: 'left',
            }}
          >
            📰 Latest News
          </button>
        </div>

        <div style={{ marginTop: 'auto', paddingTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
          <p style={{ fontSize: '12px', opacity: 0.6, lineHeight: '1.6' }}>
            MAGMA provides suggestions only. You are responsible for all trading decisions.
          </p>
        </div>
      </aside>
    </>
  );
}

