import { getRestaurant, getCategories } from '@/lib/api';
import TopBar from '@/components/TopBar';
import SideMenu from '@/components/SideMenu';
import IntroManager from '@/components/IntroManager';
import Link from 'next/link';
import Image from 'next/image';
import type { Metadata } from 'next';
import Cart from '@/components/Cart';
import WifiHelper from '@/components/WifiHelper';

export const revalidate = 60; // 60초마다 ISR 재생성

export async function generateMetadata({
  params,
}: {
  params: Promise<{ restaurantSlug: string }>;
}): Promise<Metadata> {
  const { restaurantSlug } = await params;
  try {
    const restaurant = await getRestaurant(restaurantSlug);
    return {
      title: `${restaurant.name} | 스마트 메뉴판`,
      description: `${restaurant.name} 매장의 실시간 모바일 QR 메뉴판입니다.`,
      openGraph: {
        images: restaurant.site_settings?.logo_image ? [{ url: restaurant.site_settings.logo_image }] : [],
      },
    };
  } catch {
    return {
      title: '스마트 메뉴판',
    };
  }
}

import { notFound } from 'next/navigation';

export default async function MenuMainPage({
  params,
}: {
  params: Promise<{ restaurantSlug: string }>;
}) {
  const { restaurantSlug } = await params;
  
  let restaurant;
  let categories;

  try {
    [restaurant, categories] = await Promise.all([
      getRestaurant(restaurantSlug),
      getCategories(restaurantSlug),
    ]);
  } catch (error) {
    console.error('Failed to fetch restaurant or categories:', error);
    notFound();
  }

  const settings = restaurant.site_settings;
  const showIntroImage = !!(settings && settings.intro_image);

  return (
    <>
      <TopBar />
      <SideMenu />

      {/* 로딩 인트로 및 설명서 카드 제어 */}
      <IntroManager
        introVideo={settings?.intro_video || null}
        manualVideo={settings?.loading_video_2 || null}
        showManualCard={settings?.show_manual_card || false}
      />

      <main className="main" style={{ padding: showIntroImage ? '0' : '60px 0 0 0' }}>
        <div className="container" style={{ padding: '0', margin: '0', maxWidth: 'none' }}>
          {showIntroImage && settings?.intro_image && (
            <div className="intro-section" style={{ margin: '0', padding: '0' }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={settings.intro_image}
                alt="Menu Introduction"
                className="intro-image"
                style={{ margin: '0', padding: '0', display: 'block', width: '100%', height: 'auto' }}
              />
            </div>
          )}

          <div className="category-section">
            <div className="category-grid">
              {/* 메뉴판 설명서 카드는 IntroManager 내부에서 렌더링되도록 하였음 (순서 일치를 위해 맨 위에 위치) */}
              
              {categories.map((category) => (
                <Link
                  href={`/${restaurantSlug}/category/${category.id}`}
                  className="category-card"
                  key={category.id}
                >
                  {category.name_en && (
                    <p className="category-name-en">{category.name_en}</p>
                  )}
                  <h3 className="category-name-ko">{category.name}</h3>
                </Link>
              ))}

              {categories.length === 0 && !settings?.show_manual_card && (
                <div className="no-categories">
                  등록된 카테고리가 없습니다.
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
      
      <Cart />
      <WifiHelper />
    </>
  );
}
