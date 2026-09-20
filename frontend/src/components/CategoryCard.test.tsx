import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import CategoryCard from './CategoryCard';
import type { CardLayout } from '@/lib/layout';
import type { Category } from '@/lib/types';

/**
 * 손님이 보는 카테고리 카드.
 *
 * 여기서 지키려는 건 둘이다. 손대지 않은 매장이 예전 그대로 그려질 것,
 * 그리고 사장님이 고친 배치가 실제로 화면에 반영될 것.
 *
 * 앞의 것이 더 중요하다 — 거기가 틀리면 배포하는 순간 영업 중인 매장의
 * 손님 화면이 전부 바뀐다.
 */

const CATEGORY = {
  id: 1,
  name: '안주',
  name_en: 'Anju',
  category_image: 'https://example.test/anju.webp',
  hide_side_image: false,
} as Category;

function custom(overrides: Partial<Record<string, unknown>>[] = []): CardLayout {
  return {
    layout_type: 'custom',
    components: [
      { id: 'category_image', name: '이미지', visible: true, x: 0, y: 0, w: 100, h: 65 },
      { id: 'category_name', name: '한글', visible: true, x: 5, y: 70, w: 90, h: 15 },
      { id: 'category_name_en', name: '영문', visible: true, x: 5, y: 85, w: 90, h: 10 },
      ...overrides,
    ] as CardLayout['components'],
  };
}

describe('손대지 않은 매장', () => {
  it('예전 마크업 그대로 그린다', () => {
    const { container } = render(
      <CategoryCard category={CATEGORY} href="/bid/category/1" layout={null} />,
    );
    const card = container.querySelector('.category-card');

    expect(card).toBeTruthy();
    expect(card?.classList.contains('category-card-custom')).toBe(false);
    expect(card?.getAttribute('style')).toBeNull();
  });

  it('layout_type 이 default 여도 예전 그대로다', () => {
    const { container } = render(
      <CategoryCard
        category={CATEGORY}
        href="/bid/category/1"
        layout={{ layout_type: 'default', components: custom().components }}
      />,
    );
    expect(container.querySelector('.category-card-custom')).toBeNull();
  });

  it('이미지는 그리지 않는다', () => {
    // 예전 카드에는 이미지 자리가 없었다. 여기서 갑자기 그리면 손대지 않은
    // 매장의 화면이 바뀐다.
    const { container } = render(
      <CategoryCard category={CATEGORY} href="/bid/category/1" layout={null} />,
    );
    expect(container.querySelector('img')).toBeNull();
  });
});

describe('배치를 고친 매장', () => {
  it('빌더에서 정한 자리에 놓는다', () => {
    const { container } = render(
      <CategoryCard
        category={CATEGORY}
        href="/x/category/1"
        layout={custom([{ id: 'category_name', name: '한글', visible: true, x: 10, y: 20, w: 80, h: 12 }])}
      />,
    );
    const box = screen.getByText('안주').parentElement;

    expect(box?.getAttribute('style')).toContain('left: 10%');
    expect(box?.getAttribute('style')).toContain('top: 20%');
  });

  it('숨긴 조각은 그리지 않는다', () => {
    render(
      <CategoryCard
        category={CATEGORY}
        href="/x/category/1"
        layout={custom([{ id: 'category_name_en', name: '영문', visible: false, x: 5, y: 85, w: 90, h: 10 }])}
      />,
    );
    expect(screen.queryByText('Anju')).toBeNull();
    expect(screen.getByText('안주')).toBeTruthy();
  });

  it('이미지 조각이 켜져 있으면 그린다', () => {
    const { container } = render(
      <CategoryCard category={CATEGORY} href="/x/category/1" layout={custom()} />,
    );
    expect(container.querySelector('img')?.getAttribute('src')).toBe(CATEGORY.category_image);
  });

  it('이미지가 없는 카테고리는 빈 상자를 남기지 않는다', () => {
    const { container } = render(
      <CategoryCard
        category={{ ...CATEGORY, category_image: null } as Category}
        href="/x/category/1"
        layout={custom()}
      />,
    );
    expect(container.querySelector('img')).toBeNull();
  });

  it('카드가 빌더 캔버스와 같은 비율을 갖는다', () => {
    const { container } = render(
      <CategoryCard category={CATEGORY} href="/x/category/1" layout={custom()} />,
    );
    expect(container.querySelector('.category-card-custom')?.getAttribute('style'))
      .toContain('aspect-ratio: 4 / 3');
  });

  it('사장님이 맞춰 둔 글꼴을 나르는 클래스를 유지한다', () => {
    // 폰트·색·크기는 styles.ts 가 이 클래스들에 CSS 변수로 주입한다.
    const { container } = render(
      <CategoryCard category={CATEGORY} href="/x/category/1" layout={custom()} />,
    );
    expect(container.querySelector('.category-name-ko')).toBeTruthy();
    expect(container.querySelector('.category-name-en')).toBeTruthy();
  });

  it('망가진 배치가 와도 메뉴는 보인다', () => {
    // 사장님이 이상한 값을 저장해도 손님 화면이 비면 안 된다. 그건 사장님도
    // 모르는 채 영업이 멈추는 것이다.
    const broken = { layout_type: 'custom', components: '없음' } as unknown as CardLayout;
    render(<CategoryCard category={CATEGORY} href="/x/category/1" layout={broken} />);

    expect(screen.getByText('안주')).toBeTruthy();
  });
});
