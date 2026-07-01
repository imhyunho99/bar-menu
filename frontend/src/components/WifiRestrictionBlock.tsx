'use client';

import type { SiteSettings } from '@/lib/types';

export default function WifiRestrictionBlock({
  settings,
}: {
  settings: SiteSettings;
  clientIp: string;
}) {
  return (
    <div className="wifi-block-container" style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      backgroundColor: '#080710',
      color: '#ffffff',
      fontFamily: 'sans-serif',
      padding: '20px',
      textAlign: 'center'
    }}>
      <div className="wifi-block-card" style={{
        maxWidth: '380px',
        width: '100%',
        padding: '40px 30px',
        borderRadius: '16px',
        background: 'rgba(255, 255, 255, 0.03)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}>
        {settings.logo_image && (
          <div style={{ marginBottom: '25px', width: '75px', height: '75px', borderRadius: '50%', overflow: 'hidden' }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={settings.logo_image} alt="Logo" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
        )}
        
        <h2 style={{ fontSize: '1.4rem', fontWeight: '600', marginBottom: '15px', wordBreak: 'keep-all', color: '#ffffff' }}>
          와이파이 접속 후 사용해 주세요
        </h2>
        
        <p style={{ fontSize: '0.95rem', color: '#a0a0ab', lineHeight: '1.6', marginBottom: '35px', wordBreak: 'keep-all' }}>
          본 메뉴판은 매장 와이파이 네트워크에 연결된 상태에서만 조회가 가능합니다.
        </p>

        <button 
          onClick={() => window.location.reload()}
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '10px',
            border: 'none',
            background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
            color: '#ffffff',
            fontWeight: '600',
            fontSize: '1rem',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)',
          }}
        >
          새로고침 ↻
        </button>
      </div>
    </div>
  );
}
