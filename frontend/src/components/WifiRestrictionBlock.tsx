'use client';

import { useState } from 'react';
import type { SiteSettings } from '@/lib/types';

/**
 * 주소C — 내부 네트워크(매장 와이파이) 미연결 시 표시되는 잠금화면.
 * layout.tsx(서버측 IP 게이트)와 WifiRestrictionWrapper(클라이언트측 SSID 게이트)
 * 두 곳에서 렌더된다.
 *
 * 버튼 흐름:
 *  1) "내부 네트워크 연결하기" → 매장 와이파이 정보(이름/비번) 표시 + 연결 안내
 *  2) "연결했어요 · 계속" → 주소A(/{slug}/enter)로 이동해 IP 재확인
 * (브라우저는 폰을 와이파이에 자동 연결시킬 수 없으므로, 안내 후 재확인하는 방식)
 */
export default function WifiRestrictionBlock({
  settings,
  slug,
}: {
  settings: SiteSettings;
  slug: string;
  clientIp?: string;
}) {
  const [showWifiInfo, setShowWifiInfo] = useState(false);
  const [copied, setCopied] = useState<'ssid' | 'password' | null>(null);

  const ssid = settings.wifi_ssid || '';
  const password = settings.wifi_password || '';
  const hasWifiInfo = !!ssid;

  const goEnter = () => {
    window.location.href = `/${slug}/enter`;
  };

  const handleConnectClick = () => {
    // 안내할 와이파이 정보가 없으면 바로 재진입
    if (!hasWifiInfo) {
      goEnter();
      return;
    }
    setShowWifiInfo(true);
  };

  const copyToClipboard = async (text: string, which: 'ssid' | 'password') => {
    if (!text) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
      }
      setCopied(which);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      /* 복사 실패는 조용히 무시 (사용자가 직접 입력 가능) */
    }
  };

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#000000',
    color: '#ffffff',
    fontFamily: 'sans-serif',
    padding: '32px 24px',
    textAlign: 'center',
  };

  const pillButtonStyle: React.CSSProperties = {
    width: '100%',
    maxWidth: '360px',
    padding: '18px 20px',
    borderRadius: '999px',
    border: 'none',
    background: '#3a3a3a',
    color: '#ffffff',
    cursor: 'pointer',
    lineHeight: 1.3,
  };

  if (showWifiInfo) {
    return (
      <div style={containerStyle}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '28px', wordBreak: 'keep-all' }}>
          매장 와이파이에 연결해 주세요
        </h2>

        <div style={{ width: '100%', maxWidth: '360px', display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '28px' }}>
          <WifiField label="네트워크 이름 (SSID)" value={ssid} onCopy={() => copyToClipboard(ssid, 'ssid')} copied={copied === 'ssid'} />
          {password && (
            <WifiField label="비밀번호" value={password} onCopy={() => copyToClipboard(password, 'password')} copied={copied === 'password'} />
          )}
        </div>

        <p style={{ fontSize: '0.9rem', color: '#a0a0ab', lineHeight: 1.6, marginBottom: '32px', wordBreak: 'keep-all', maxWidth: '340px' }}>
          휴대폰 설정 &gt; Wi-Fi 에서 위 네트워크에 연결한 뒤, 아래 버튼을 눌러 주세요.
        </p>

        <button onClick={goEnter} style={{ ...pillButtonStyle, background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)' }}>
          <span style={{ fontSize: '1.05rem', fontWeight: 700 }}>연결했어요 · 계속</span>
        </button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <h1 style={{ fontSize: '1.9rem', fontWeight: 700, lineHeight: 1.5, marginBottom: '28px', wordBreak: 'keep-all' }}>
        보안을 위해<br />
        내부 네트워크에<br />
        연결된 상태로만<br />
        조회가 가능합니다.
      </h1>

      <p style={{ fontSize: '0.95rem', color: '#8a8a93', letterSpacing: '0.02em', lineHeight: 1.6, marginBottom: '56px', wordBreak: 'keep-all', maxWidth: '360px' }}>
        For Security, Please connect to the private network before you proceed
      </p>

      <button onClick={handleConnectClick} style={pillButtonStyle}>
        <span style={{ display: 'block', fontSize: '1.15rem', fontWeight: 700 }}>내부 네트워크 연결하기</span>
        <span style={{ display: 'block', fontSize: '0.9rem', color: '#a0a0ab', letterSpacing: '0.03em', marginTop: '2px' }}>Connect to the Network</span>
      </button>
    </div>
  );
}

function WifiField({ label, value, onCopy, copied }: { label: string; value: string; onCopy: () => void; copied: boolean }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '12px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
      <div style={{ textAlign: 'left', overflow: 'hidden' }}>
        <div style={{ fontSize: '0.72rem', color: '#8a8a93', marginBottom: '2px' }}>{label}</div>
        <div style={{ fontSize: '1.05rem', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{value}</div>
      </div>
      <button
        onClick={onCopy}
        style={{ flexShrink: 0, padding: '8px 14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)', background: 'transparent', color: '#ffffff', fontSize: '0.85rem', cursor: 'pointer' }}
      >
        {copied ? '복사됨' : '복사'}
      </button>
    </div>
  );
}
