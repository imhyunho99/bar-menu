import { getRestaurant, getCategoryTree } from '@/lib/api';
import { buildCSSVariables, buildFontFaces } from '@/lib/styles';
import type { RestaurantDetail, CategoryTree } from '@/lib/types';
import { RestaurantProvider } from './context';
import { redirect } from 'next/navigation';
import { headers } from 'next/headers';
import WifiRestrictionBlock from '@/components/WifiRestrictionBlock';
import { Suspense } from 'react';
import WifiRestrictionWrapper from '@/components/WifiRestrictionWrapper';
import ScreenshotBlocker from '@/components/ScreenshotBlocker';

export default async function RestaurantLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ restaurantSlug: string }>;
}) {
  const { restaurantSlug } = await params;

  if (restaurantSlug === 'admin') {
    redirect('http://localhost:8000/admin/');
  }

  let restaurant: RestaurantDetail;
  let categoryTree: CategoryTree[];

  try {
    [restaurant, categoryTree] = await Promise.all([
      getRestaurant(restaurantSlug),
      getCategoryTree(restaurantSlug),
    ]);
  } catch {
    redirect('/');
  }

  const settings = restaurant.site_settings;

  // x-pathname 헤더 확인 (QR 코드 인쇄 페이지 바이패스용)
  const headerList = await headers();
  const pathname = headerList.get('x-pathname') || '';
  const isQrPage = pathname.endsWith('/qr') || pathname.endsWith('/qr/');

  // 매장 와이파이(공인 IP) 접속 제한 확인
  if (!isQrPage && settings && settings.restrict_by_ip && settings.store_public_ip) {
    const xForwardedFor = headerList.get('x-forwarded-for');
    let clientIp = xForwardedFor 
      ? xForwardedFor.split(',')[0].trim() 
      : headerList.get('x-real-ip') || '127.0.0.1';

    // ::ffff: 접두사 제거 (IPv4-mapped IPv6 주소 노멀라이즈)
    if (clientIp.startsWith('::ffff:')) {
      clientIp = clientIp.substring(7);
    }

    // 로컬 접속(127.0.0.1, ::1) 및 매장 공인 IP 접속 여부 확인
    const isLocal = clientIp === '127.0.0.1' || 
                    clientIp === '::1' || 
                    clientIp === 'localhost';
    const ipMatches = clientIp === settings.store_public_ip;

    if (!isLocal && !ipMatches) {
      return <WifiRestrictionBlock settings={settings} clientIp={clientIp} />;
    }
  }
  const cssVars = buildCSSVariables(settings);
  const fontFaces = buildFontFaces(settings);

  return (
    <>
      {(cssVars || fontFaces) && (
        <style dangerouslySetInnerHTML={{ __html: `${fontFaces}\n${cssVars}` }} />
      )}
      {!isQrPage && settings?.side_image && (
        <style dangerouslySetInnerHTML={{
          __html: `body { background: url('${settings.side_image}'); background-size: cover; background-position: center; background-attachment: fixed; }`
        }} />
      )}
      <RestaurantProvider restaurant={restaurant} categoryTree={categoryTree}>
        <div style={{ backgroundColor: isQrPage ? '#000000' : (settings?.background_color || '#000000'), minHeight: '100vh' }}>
          <Suspense fallback={<div style={{ color: '#fff', textAlign: 'center', padding: '2rem' }}>로딩 중...</div>}>
            <WifiRestrictionWrapper>
              <ScreenshotBlocker />
              {children}
            </WifiRestrictionWrapper>
          </Suspense>
        </div>
      </RestaurantProvider>
    </>
  );
}
