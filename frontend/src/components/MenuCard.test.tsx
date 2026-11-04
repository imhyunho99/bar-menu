import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import MenuCard from './MenuCard';
import { RestaurantProvider } from '@/app/[restaurantSlug]/context';
import type { CardLayout } from '@/lib/layout';
import type { MenuItem, RestaurantDetail } from '@/lib/types';

/**
 * 어느 카드로 그릴지 고르는 갈림길.
 *
 * MenuCard 는 display_mode 로 이미 네 갈래다. 여기서 지키는 건 '배치를 고친
 * 매장만 다섯 번째 갈래로 가고, 나머지는 예전 그대로' 다. 이게 틀리면
 * 배포하는 순간 영업 중인 매장 전부의 손님 화면이 바뀐다.
 */

const ITEM = {
  id: 7,
  name: '골뱅이무침',
  name_en: 'Whelk Salad',
  price: '18,000',
  description: '소면 포함',
  notes: null,
  menu_image: null,
  display_mode: 'auto',
  click_expand: false,
  enable_detail_view: false,
  lightbox_style: 'default',
  lightbox_opacity: 80,
  pairings: [],
} as unknown as MenuItem;

// 사진 조각을 끈 배치. ITEM 에는 사진이 없어서, 사진 자리를 남겨 둔 배치면
// 예전 카드로 간다(아래 '사진 없는 메뉴' 참고).
const CUSTOM: CardLayout = {
  layout_type: 'custom',
  components: [
    { id: 'menu_image', name: '이미지', visible: false, x: 0, y: 0, w: 100, h: 50 },
    { id: 'menu_name', name: '메뉴명', visible: true, x: 5, y: 55, w: 90, h: 12 },
  ],
};

/** 사진 자리를 위쪽 절반에 남겨 둔 배치 — 기본 자리 그대로. */
const WITH_PHOTO_SLOT: CardLayout = {
  layout_type: 'custom',
  components: [{ id: 'menu_price', name: '가격', visible: true, x: 5, y: 78, w: 90, h: 10 }],
};

function draw(layout: CardLayout | null, enableCart = true, item: MenuItem = ITEM) {
  const restaurant = {
    slug: 'bid',
    site_settings: { enable_cart: enableCart },
  } as unknown as RestaurantDetail;

  return render(
    <RestaurantProvider restaurant={restaurant} categoryTree={[]}>
      <MenuCard item={item} layout={layout} />
    </RestaurantProvider>,
  );
}

describe('어느 카드로 그리는가', () => {
  it('손대지 않은 매장은 예전 카드로 간다', () => {
    const { container } = draw(null);

    expect(container.querySelector('.menu-item')).toBeTruthy();
    expect(container.querySelector('.menu-item-custom')).toBeNull();
    expect(container.querySelector('.menu-content')).toBeTruthy();
  });

  it('layout_type 이 default 면 고친 적 없는 것으로 본다', () => {
    const { container } = draw({ ...CUSTOM, layout_type: 'default' });
    expect(container.querySelector('.menu-item-custom')).toBeNull();
  });

  it('배치를 고친 매장만 절대배치 카드로 간다', () => {
    const { container } = draw(CUSTOM);

    expect(container.querySelector('.menu-item-custom')).toBeTruthy();
    expect(container.querySelector('.menu-content')).toBeNull();
    expect(screen.getByText('골뱅이무침')).toBeTruthy();
  });

  it('사진 자리를 남긴 배치에 사진 없는 메뉴는 예전 카드로 간다', () => {
    // 위쪽 절반이 빈 카드가 줄줄이 이어지고, 영문 이름이 사진 전제의 작은
    // 상자에 갇혀 잘렸다(2026-11 bid, 32개 중 사진 2개).
    const { container } = draw(WITH_PHOTO_SLOT);

    expect(container.querySelector('.menu-item-custom')).toBeNull();
    expect(container.querySelector('.menu-content')).toBeTruthy();
    expect(screen.getByText('Whelk Salad')).toBeTruthy();
  });

  it('같은 배치라도 사진이 있는 combined 메뉴는 사장님이 놓은 대로 그린다', () => {
    const withPhoto = {
      ...ITEM,
      display_mode: 'combined',
      menu_image: 'https://example.test/x.webp',
    } as MenuItem;
    const { container } = draw(WITH_PHOTO_SLOT, true, withPhoto);

    expect(container.querySelector('.menu-item-custom')).toBeTruthy();
  });

  it('사진이 있는 auto 메뉴는 배치를 고친 매장에서도 그림만 그린다', () => {
    // 예전 카드에서 auto + 사진은 그림만 그린다. bid 의 구역 배너는 전부
    // 이 모양이었고, 배치대로 그리자 '[ Starter ]', '-' 가 밑에 드러났다.
    const banner = { ...ITEM, menu_image: 'https://example.test/banner.webp' } as MenuItem;
    const { container } = draw(WITH_PHOTO_SLOT, true, banner);

    expect(container.querySelector('.menu-item-custom')).toBeNull();
    expect(container.querySelector('.menu-only-image')).toBeTruthy();
    expect(screen.queryByText('골뱅이무침')).toBeNull();
  });

  it('image_only 메뉴는 배치를 고친 매장에서도 그림만 그린다', () => {
    // 구역 머리 배너다. 배치대로 그리면 밑에 자리채움 글자가 나온다.
    const banner = {
      ...ITEM,
      display_mode: 'image_only',
      menu_image: 'https://example.test/banner.webp',
    } as MenuItem;
    const { container } = draw(WITH_PHOTO_SLOT, true, banner);

    expect(container.querySelector('.menu-item-custom')).toBeNull();
    expect(container.querySelector('.menu-only-image')).toBeTruthy();
    expect(screen.queryByText('골뱅이무침')).toBeNull();
  });

  it('망가진 배치는 예전 카드로 떨어뜨린다', () => {
    // 손님 화면이 비는 것보다 예전 모습이 낫다.
    const broken = { layout_type: 'custom', components: '없음' } as unknown as CardLayout;
    const { container } = draw(broken);

    expect(container.querySelector('.menu-item-custom')).toBeNull();
    expect(screen.getByText('골뱅이무침')).toBeTruthy();
  });

  it('장바구니 설정은 절대배치 카드에도 그대로 간다', () => {
    // 갈래마다 따로 읽으면 custom 매장만 버튼이 없는 일이 생긴다.
    expect(draw(CUSTOM, false).container.querySelector('.add-cart-btn')).toBeNull();
    expect(draw(CUSTOM, true).container.querySelector('.add-cart-btn')).toBeTruthy();
  });
});
