import { getRestaurant, getCategories, isMenuClosed } from '@/lib/api.server';
import MenuNotOpen from '@/components/MenuNotOpen';
import CategoryCard from '@/components/CategoryCard';
import TopBar from '@/components/TopBar';
import SideMenu from '@/components/SideMenu';
import IntroManager from '@/components/IntroManager';
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
    // 결제 전 매장은 없어진 매장이 아니다. 404 로 떨구면 손님에게 폐업으로 읽힌다.
    if (isMenuClosed(error)) {
      return <MenuNotOpen />;
    }
    console.error('Failed to fetch restaurant or categories:', error);
    notFound();
  }

  const settings = restaurant.site_settings;
  const showIntroImage = !!(settings && settings.intro_image);

  return (
    <>
      <TopBar />
      <SideMenu />

      {/*
        인트로 영상은 여기서 튼다.

        한때 /enter 로 옮겼다가 되돌렸다. 옮긴 쪽에는 **1시간 쿨다운이 따라가지
        않아서**(자체 플레이어를 들고 있었다) 손님이 QR 을 찍을 때마다 영상이
        처음부터 다시 나왔다. 메뉴를 보다 다시 찍으면 또 나온다.
        쿨다운은 IntroManager 안에 있고, autoPlayIntro 가 꺼져 있으면 그 코드에
        아예 들어가지 않는다 — 그래서 '코드는 있는데 안 도는' 상태였다.
      */}
      <IntroManager
        introVideo={settings?.intro_video || null}
        manualVideo={settings?.loading_video_2 || null}
        showManualCard={settings?.show_manual_card || false}
        autoPlayIntro
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
                <CategoryCard
                  key={category.id}
                  category={category}
                  href={`/${restaurantSlug}/category/${category.id}`}
                  layout={settings?.category_card_layout_json}
                />
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
