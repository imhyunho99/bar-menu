'use client';

import { useState } from 'react';
import { useRestaurant } from '@/app/[restaurantSlug]/context';

export default function WifiHelper() {
  const { restaurant } = useRestaurant();
  const settings = restaurant.site_settings;

  const [isOpen, setIsOpen] = useState(false);
  const [copiedSSID, setCopiedSSID] = useState(false);
  const [copiedPW, setCopiedPW] = useState(false);

  if (!settings || !settings.enable_wifi || !settings.wifi_ssid) {
    return null;
  }

  const ssid = settings.wifi_ssid;
  const password = settings.wifi_password || '';
  const security = settings.wifi_security || 'WPA';

  // WiFi QR Code Standard Format: WIFI:S:SSID;T:WPA;P:PASSWORD;;
  const wifiQrData = `WIFI:S:${ssid};T:${security};P:${password};;`;
  const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&color=ffffff&bgcolor=000000&data=${encodeURIComponent(
    wifiQrData
  )}`;

  const copyToClipboard = (text: string, setCopiedFlag: (flag: boolean) => void) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        setCopiedFlag(true);
        setTimeout(() => setCopiedFlag(false), 2000);
      });
    } else {
      // Fallback
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setCopiedFlag(true);
        setTimeout(() => setCopiedFlag(false), 2000);
      } catch (err) {
        console.error('Fallback copy failed', err);
      }
      document.body.removeChild(textArea);
    }
  };

  return (
    <>
      {/* Floating WiFi wave button */}
      <button className="wifi-floating-btn" onClick={() => setIsOpen(true)}>
        <span className="wifi-btn-icon">📶</span>
        <span className="wifi-btn-text">WIFI 연결</span>
      </button>

      {/* WiFi Detail Modal */}
      {isOpen && (
        <>
          <div className="wifi-modal-overlay" onClick={() => setIsOpen(false)}></div>
          <div className="wifi-card-modal">
            <div className="wifi-modal-header">
              <h3>매장 와이파이 간편 연결</h3>
              <button className="wifi-close-btn" onClick={() => setIsOpen(false)}>&times;</button>
            </div>

            <div className="wifi-modal-body">
              <div className="wifi-detail-row">
                <div className="wifi-detail-info">
                  <span className="wifi-label">와이파이 이름 (SSID)</span>
                  <strong className="wifi-value">{ssid}</strong>
                </div>
                <button
                  className={`wifi-copy-btn ${copiedSSID ? 'copied' : ''}`}
                  onClick={() => copyToClipboard(ssid, setCopiedSSID)}
                >
                  {copiedSSID ? '복사 완료' : '복사'}
                </button>
              </div>

              {password && (
                <div className="wifi-detail-row">
                  <div className="wifi-detail-info">
                    <span className="wifi-label">비밀번호 (Password)</span>
                    <strong className="wifi-value">{password}</strong>
                  </div>
                  <button
                    className={`wifi-copy-btn ${copiedPW ? 'copied' : ''}`}
                    onClick={() => copyToClipboard(password, setCopiedPW)}
                  >
                    {copiedPW ? '복사 완료' : '복사'}
                  </button>
                </div>
              )}

              <div className="wifi-qr-section">
                <p>다른 스마트폰으로 아래 QR 코드를 카메라로 스캔하면 와이파이에 자동으로 즉시 연결됩니다.</p>
                <div className="wifi-qr-wrapper">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={qrCodeUrl} alt="WiFi Connection QR Code" />
                </div>
              </div>
            </div>

            <div className="wifi-modal-footer">
              <button className="wifi-confirm-btn" onClick={() => setIsOpen(false)}>확인</button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
