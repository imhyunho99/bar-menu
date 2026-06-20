'use client';

import { useState, useEffect } from 'react';
import { getQRCode } from '@/lib/api';

export default function QrRenderer({ slug }: { slug: string }) {
  const [qrBase64, setQrBase64] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchQR = async () => {
      try {
        // 호스트 네임 (Vercel 배포 주소 또는 로컬 주소)을 전달하여 해당 프론트엔드로 접속하는 QR 생성
        const origin = window.location.origin;
        const res = await getQRCode(slug, origin);
        setQrBase64(res.qr_image);
      } catch (err) {
        setError('QR 코드를 불러오는 데 실패했습니다.');
        console.error(err);
      }
    };
    fetchQR();
  }, [slug]);

  if (error) {
    return <div style={{ color: '#ff4757', padding: '2rem', textAlign: 'center' }}>{error}</div>;
  }

  if (!qrBase64) {
    return <div style={{ color: '#aaa', padding: '2rem', textAlign: 'center' }}>QR 코드 생성 중...</div>;
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={`data:image/png;base64,${qrBase64}`} alt="Menu QR Code" />
  );
}
