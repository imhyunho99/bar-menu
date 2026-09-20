/**
 * 저장된 카드 레이아웃을 화면에 옮기는 규칙.
 *
 * 값이 빌더(Django 템플릿의 CSS)와 여기 둘로 나뉘어 있다. 갈리면 사장님이
 * 맞춰 놓은 배치가 손님 화면에서 어긋나고, 그 어긋남은 화면에 아무 표시도
 * 남기지 않는다. menu/tests_layout_contract.py 가 두 값을 대조한다.
 */

import type { CSSProperties } from 'react';

export type CardKind = 'category' | 'menu';

/**
 * 카드의 가로세로 비율. 빌더 캔버스와 같아야 WYSIWYG 이 성립한다.
 * 종류마다 다르다 — 카테고리 320×240, 메뉴 320×440.
 */
export const CARD_ASPECT: Record<CardKind, string> = {
  category: '4 / 3',
  menu: '8 / 11',
};

/** 렌더러가 아는 조각들. 기본값(menu/models.py)과 같아야 한다. */
export const CATEGORY_COMPONENT_IDS = ['category_image', 'category_name', 'category_name_en'];
export const MENU_COMPONENT_IDS = [
  'menu_image',
  'menu_name',
  'menu_name_en',
  'menu_price',
  'menu_description',
];

export interface LayoutComponent {
  id: string;
  name: string;
  visible: boolean;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface CardLayout {
  layout_type: string;
  components: LayoutComponent[];
}

/**
 * 이 매장이 배치를 직접 고쳤는가.
 *
 * 'default' 인 매장은 오늘 코드 그대로 그린다. 이 스위치가 없으면 배포하는
 * 순간 손대지 않은 매장까지 전부 새 배치로 바뀐다.
 */
export function isCustomLayout(layout: CardLayout | null | undefined): boolean {
  return !!layout && layout.layout_type === 'custom' && Array.isArray(layout.components);
}

/**
 * 그릴 조각들. 저장된 값을 기본값 위에 덮는다.
 *
 * 저장된 JSON 에 없는 id 는 기본값의 자리와 visible 을 그대로 쓴다. 지금
 * 저장된 값들에는 나중에 추가되는 조각이 들어 있지 않은데, 없는 것을
 * '숨김' 으로 읽으면 사장님이 켜는 순간 그 조각이 통째로 사라진다.
 */
export function resolveComponents(
  layout: CardLayout,
  defaults: LayoutComponent[],
): LayoutComponent[] {
  const saved = new Map(layout.components.map((c) => [c.id, c]));
  return defaults.map((fallback) => ({ ...fallback, ...(saved.get(fallback.id) ?? {}) }));
}

/** 조각 하나를 카드 안에 놓는 style. 좌표는 카드 크기에 대한 %다. */
export function boxStyle(component: LayoutComponent): CSSProperties {
  return {
    position: 'absolute',
    left: `${component.x}%`,
    top: `${component.y}%`,
    width: `${component.w}%`,
    height: `${component.h}%`,
    overflow: 'hidden',
  };
}
