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
  'cart_button',
  'menu_notes',
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
 * 이 카드를 절대배치로 그릴 것인가 — 배치를 고쳤고, 그 배치가 이 카드에 맞는가.
 *
 * 사진 조각이 켜진 배치는 카드의 그 자리를 사진 몫으로 비워 둔다(기본값은
 * 위쪽 절반). 사진이 없는 메뉴를 거기 그리면 위쪽 절반이 통째로 빈 카드가
 * 줄줄이 이어지고, 글자는 사진을 전제로 작게 잡은 상자에 갇혀 잘린다.
 * 2026-11 bid: 한 카테고리 32개 중 사진은 2개였고, 영문 이름 상자가 폰에서
 * 38px 인데 글자는 34px 에 2~4줄이라 첫 줄만 남았다.
 *
 * 그런 카드는 예전 카드로 그린다. 사진을 끈 배치(글자만 놓은 배치)는 사진
 * 유무와 상관없이 사장님이 놓은 대로 그린다.
 */
export function drawsCustom(
  layout: CardLayout | null | undefined,
  defaults: LayoutComponent[],
  imageId: string,
  hasImage: boolean,
): layout is CardLayout {
  if (!isCustomLayout(layout)) return false;
  if (hasImage) return true;
  const slot = resolveComponents(layout as CardLayout, defaults).find((c) => c.id === imageId);
  return !slot?.visible;
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
  // 빌더는 저장할 때 이미 거른다(widget 의 mergeWithDefaults). 여기서도 걸러야
  // 한다 — JSONField 에는 검증이 없고 admin 의 textarea 로 아무거나 들어온다.
  // components: [null] 하나로 손님 화면이 통째로 에러 화면이 됐다.
  const saved = new Map(
    layout.components.filter((c) => c && c.id).map((c) => [c.id, c]),
  );
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
