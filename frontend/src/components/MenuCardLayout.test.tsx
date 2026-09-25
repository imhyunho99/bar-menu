import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import MenuCardLayout from './MenuCardLayout';
import type { CardLayout, LayoutComponent } from '@/lib/layout';
import type { MenuItem } from '@/lib/types';

/**
 * 배치를 고친 매장의 메뉴 카드.
 *
 * 카테고리 카드와 달리 여기에는 손님이 누르는 것이 있다 — 장바구니 버튼.
 * 그래서 '그려지는가' 만큼 '눌렀을 때 담기는가' 가 중요하다. custom 매장만
 * 조용히 안 담기면 사장님은 주문이 없는 줄 안다.
 */

const ITEM = {
  id: 7,
  name: '골뱅이무침',
  name_en: 'Whelk Salad',
  price: '18,000',
  description: '소면 포함',
  notes: '매움',
  menu_image: 'https://example.test/golbaengi.webp',
  click_expand: false,
} as MenuItem;

function layoutOf(...overrides: LayoutComponent[]): CardLayout {
  return { layout_type: 'custom', components: overrides };
}

function draw(item: MenuItem, enableCart = true, layout: CardLayout = layoutOf()) {
  return render(
    <MenuCardLayout item={item} layout={layout} enableCart={enableCart} onImageClick={() => {}} />,
  );
}

describe('무엇을 그리는가', () => {
  it('빌더 기본 배치를 그대로 그린다', () => {
    // 저장된 JSON 이 비어 있어도 조각은 전부 기본 자리에 나와야 한다.
    // 여기가 비면 결제한 사장님이 빌더를 열자마자 빈 카드를 본다.
    draw(ITEM);

    expect(screen.getByText('골뱅이무침')).toBeTruthy();
    expect(screen.getByText('Whelk Salad')).toBeTruthy();
    expect(screen.getByText('18,000')).toBeTruthy();
    expect(screen.getByText('소면 포함')).toBeTruthy();
    expect(screen.getByText('매움')).toBeTruthy();
  });

  it('카드가 빌더 캔버스와 같은 비율을 갖는다', () => {
    // 캔버스는 320×440. 카테고리(4/3)와 같은 비율로 뭉치면 사장님이 빌더에서
    // 본 자리와 손님이 보는 자리가 어긋난다.
    const { container } = draw(ITEM);
    expect(container.querySelector('.menu-item-custom')?.getAttribute('style'))
      .toContain('aspect-ratio: 8 / 11');
  });

  it('비어 있는 값은 빈 상자를 남기지 않는다', () => {
    const { container } = draw({
      ...ITEM,
      name_en: '',
      description: '',
      notes: '',
      menu_image: null,
    } as MenuItem);

    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelectorAll('.layout-text')).toHaveLength(2); // 이름과 가격만
  });

  it('숨긴 조각은 그리지 않는다', () => {
    draw(ITEM, true, layoutOf(
      { id: 'menu_price', name: '가격', visible: false, x: 5, y: 78, w: 60, h: 10 },
    ));
    expect(screen.queryByText('18,000')).toBeNull();
    expect(screen.getByText('골뱅이무침')).toBeTruthy();
  });

  it('빌더에서 정한 자리에 놓는다', () => {
    draw(ITEM, true, layoutOf(
      { id: 'menu_name', name: '메뉴명', visible: true, x: 12, y: 34, w: 56, h: 7 },
    ));
    const box = screen.getByText('골뱅이무침').parentElement?.parentElement;

    expect(box?.getAttribute('style')).toContain('left: 12%');
    expect(box?.getAttribute('style')).toContain('top: 34%');
  });
});

describe('장바구니', () => {
  it('누르면 Cart 가 듣는 창구로 메뉴를 보낸다', () => {
    const heard = vi.fn();
    window.addEventListener('add-to-cart', heard);
    draw(ITEM);

    fireEvent.click(screen.getByRole('button'));

    expect(heard).toHaveBeenCalledOnce();
    expect((heard.mock.calls[0][0] as CustomEvent).detail).toMatchObject({ id: 7 });
    window.removeEventListener('add-to-cart', heard);
  });

  it('글자 상자에 덮여도 눌린다', () => {
    // 그리는 순서가 곧 위아래다. 노트와 설명이 기본값 배열에서 버튼보다
    // 뒤에 있어서, 사장님이 그 둘을 버튼 위로 옮기면 버튼이 덮여 눌러도
    // 아무 일이 없었다 — 주문이 조용히 안 담기고 사장님은 모른다.
    // 빌더에는 위아래를 바꿀 방법이 아예 없다.
    const { container } = draw(ITEM, true, layoutOf(
      { id: 'cart_button', name: '장바구니', visible: true, x: 70, y: 80, w: 25, h: 12 },
      { id: 'menu_notes', name: '노트', visible: true, x: 70, y: 80, w: 25, h: 12 },
    ));
    const box = container.querySelector('.add-cart-btn')?.parentElement;
    expect(box?.style.zIndex).toBe('1');
  });

  it('장바구니를 끈 매장에는 버튼이 없다', () => {
    draw(ITEM, false);
    expect(screen.queryByRole('button')).toBeNull();
  });
});
