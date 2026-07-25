'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, usePathname } from 'next/navigation';
import WifiRestrictionBlock from './WifiRestrictionBlock';
import { useRestaurant } from '@/app/[restaurantSlug]/context';

export default function WifiRestrictionWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const { restaurant } = useRestaurant();
  const settings = restaurant.site_settings;
  const slug = restaurant.slug;
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const [isVerified, setIsVerified] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // QR 코드 인쇄 페이지(/qr)는 와이파이 잠금 제외
    if (pathname && (pathname.endsWith('/qr') || pathname.endsWith('/qr/'))) {
      setIsVerified(true);
      setLoading(false);
      return;
    }

    if (!settings || !settings.restrict_by_wifi_ssid || !settings.wifi_ssid) {
      setIsVerified(true);
      setLoading(false);
      return;
    }

    // 로컬 개발 환경(localhost, 127.0.0.1)에서의 접속은 항상 허용 (테스트 편의성 제공)
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]') {
        setIsVerified(true);
        setLoading(false);
        return;
      }
    }

    // 1. sessionStorage에 이미 인증 완료된 기록이 있는지 확인
    const cachedVer = sessionStorage.getItem(`wifi_verified_${slug}`);
    if (cachedVer === 'true') {
      setIsVerified(true);
      setLoading(false);
      return;
    }

    // 2. URL Query Parameter에 wifi 매칭 정보가 있는지 확인
    const wifiParam = searchParams.get('wifi');
    if (wifiParam && wifiParam.trim().toLowerCase() === settings.wifi_ssid.trim().toLowerCase()) {
      sessionStorage.setItem(`wifi_verified_${slug}`, 'true');
      setIsVerified(true);
      setLoading(false);
      return;
    }

    // 인증 실패 상태
    setIsVerified(false);
    setLoading(false);
  }, [settings, slug, searchParams, pathname]);

  if (loading) {
    return (
      <div style={{ color: '#fff', padding: '2rem', textAlign: 'center', backgroundColor: '#000000', minHeight: '100vh' }}>
        접속 권한 확인 중...
      </div>
    );
  }

  if (!isVerified && settings) {
    // WiFi SSID 제한용 락 스크린 노출
    // 클라이언트 사이드 검증이므로 IP 대신 "WiFi 접속 상태(QR 인식)"를 안내
    return <WifiRestrictionBlock settings={settings} clientIp="SSID 미인증" slug={slug} />;
  }

  return <>{children}</>;
}
