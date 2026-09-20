import Link from 'next/link';

import {
  CARD_ASPECT,
  boxStyle,
  isCustomLayout,
  resolveComponents,
  type CardLayout,
  type LayoutComponent,
} from '@/lib/layout';
import type { Category } from '@/lib/types';

/**
 * 손님이 보는 카테고리 카드.
 *
 * 사장님이 빌더에서 배치를 고친 매장(layout_type === 'custom')만 절대배치로
 * 그린다. 손대지 않은 매장은 예전 마크업 그대로다 — 이 갈래가 없으면
 * 배포하는 순간 손대지 않은 매장까지 전부 새 배치로 바뀐다.
 */

/** 빌더 기본값과 같은 자리. 저장된 JSON 에 빠진 조각을 여기서 채운다. */
const DEFAULTS: LayoutComponent[] = [
  { id: 'category_image', name: '카테고리 이미지', visible: true, x: 0, y: 0, w: 100, h: 65 },
  { id: 'category_name', name: '카테고리명 (한글)', visible: true, x: 5, y: 70, w: 90, h: 15 },
  { id: 'category_name_en', name: '카테고리명 (영문)', visible: true, x: 5, y: 85, w: 90, h: 10 },
];

function Piece({ component, category }: { component: LayoutComponent; category: Category }) {
  if (!component.visible) return null;

  if (component.id === 'category_image') {
    if (!category.category_image) return null;
    return (
      <div style={boxStyle(component)}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={category.category_image}
          alt=""
          loading="lazy"
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />
      </div>
    );
  }

  if (component.id === 'category_name') {
    return (
      <div style={boxStyle(component)}>
        <h3 className="category-name-ko layout-text">{category.name}</h3>
      </div>
    );
  }

  if (component.id === 'category_name_en') {
    if (!category.name_en) return null;
    return (
      <div style={boxStyle(component)}>
        <p className="category-name-en layout-text">{category.name_en}</p>
      </div>
    );
  }

  return null;
}

export default function CategoryCard({
  category,
  href,
  layout,
}: {
  category: Category;
  href: string;
  layout: CardLayout | null | undefined;
}) {
  if (!isCustomLayout(layout)) {
    return (
      <Link href={href} className="category-card">
        {category.name_en && <p className="category-name-en">{category.name_en}</p>}
        <h3 className="category-name-ko">{category.name}</h3>
      </Link>
    );
  }

  return (
    <Link
      href={href}
      className="category-card category-card-custom"
      style={{ aspectRatio: CARD_ASPECT.category }}
    >
      {resolveComponents(layout as CardLayout, DEFAULTS).map((component) => (
        <Piece key={component.id} component={component} category={category} />
      ))}
    </Link>
  );
}
