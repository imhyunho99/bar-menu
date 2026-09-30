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

const CUSTOM: CardLayout = {
  layout_type: 'custom',
  components: [
    { id: 'menu_name', name: '메뉴명', visible: true, x: 5, y: 55, w: 90, h: 12 },
  ],
};

function draw(layout: CardLayout | null, enableCart = true) {
  const restaurant = {
    slug: 'bid',
    site_settings: { enable_cart: enableCart },
  } as unknown as RestaurantDetail;

  return render(
    <RestaurantProvider restaurant={restaurant} categoryTree={[]}>
      <MenuCard item={ITEM} layout={layout} />
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
