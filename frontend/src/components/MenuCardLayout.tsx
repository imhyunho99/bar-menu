'use client';

import {
  CARD_ASPECT,
  boxStyle,
  resolveComponents,
  type CardLayout,
  type LayoutComponent,
} from '@/lib/layout';
import type { MenuItem } from '@/lib/types';
import { Nl2br } from './MenuCard';

/**
 * 사장님이 빌더에서 배치를 고친 매장의 메뉴 카드.
 *
 * MenuCard 는 이미 display_mode 로 네 갈래를 그린다. 거기에 다섯 번째를
 * 끼우면 읽을 수 없어져서 갈래를 통째로 여기로 뺐다.
 *
 * custom 이면 display_mode 를 보지 않는다. 주인이 둘이면 '이미지를 보이게
 * 놓았는데 안 나온다' 가 생기고, 그걸 설명할 자리가 화면에 없다.
 */

const DEFAULTS: LayoutComponent[] = [
  { id: 'menu_image', name: '메뉴 이미지', visible: true, x: 0, y: 0, w: 100, h: 50 },
  { id: 'menu_name', name: '메뉴명 (한글)', visible: true, x: 5, y: 55, w: 90, h: 12 },
  { id: 'menu_name_en', name: '메뉴명 (영문)', visible: true, x: 5, y: 68, w: 90, h: 8 },
  { id: 'menu_price', name: '가격', visible: true, x: 5, y: 78, w: 60, h: 10 },
  { id: 'cart_button', name: '장바구니 버튼', visible: true, x: 70, y: 78, w: 25, h: 10 },
  { id: 'menu_description', name: '메뉴 설명', visible: true, x: 5, y: 89, w: 90, h: 6 },
  { id: 'menu_notes', name: '메뉴 노트', visible: true, x: 5, y: 95, w: 90, h: 5 },
];

function Piece({
  component,
  item,
  enableCart,
  onImageClick,
}: {
  component: LayoutComponent;
  item: MenuItem;
  enableCart: boolean;
  onImageClick: (e: React.MouseEvent) => void;
}) {
  if (!component.visible) return null;
  const style = boxStyle(component);

  switch (component.id) {
    case 'menu_image':
      if (!item.menu_image) return null;
      return (
        <div style={style} data-expand={item.click_expand || undefined} onClick={onImageClick}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={item.menu_image}
            alt={item.name}
            loading="lazy"
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        </div>
      );

    case 'menu_name':
      return (
        <div style={style}>
          <span className="menu-name-ko layout-text"><Nl2br text={item.name} /></span>
        </div>
      );

    case 'menu_name_en':
      if (!item.name_en) return null;
      return (
        <div style={style}>
          <span className="menu-name-en layout-text"><Nl2br text={item.name_en} /></span>
        </div>
      );

    case 'menu_price':
      return (
        <div style={style}>
          <div className="menu-price layout-text"><Nl2br text={item.price} /></div>
        </div>
      );

    case 'menu_description':
      if (!item.description) return null;
      return (
        <div style={style}>
          <div className="menu-description layout-text"><Nl2br text={item.description} /></div>
        </div>
      );

    case 'menu_notes':
      if (!item.notes) return null;
      return (
        <div style={style}>
          <span className="menu-notes layout-text"><Nl2br text={item.notes} /></span>
        </div>
      );

    case 'cart_button':
      if (!enableCart) return null;
      return (
        <div style={style}>
          <button
            className="add-cart-btn"
            style={{ width: '100%', height: '100%' }}
            onClick={(e) => {
              e.stopPropagation();
              // Cart.tsx 가 듣는 창구다. 다른 길을 만들면 custom 매장만
              // 장바구니가 조용히 안 담긴다.
              window.dispatchEvent(new CustomEvent('add-to-cart', { detail: item }));
            }}
          >
            +
          </button>
        </div>
      );

    default:
      return null;
  }
}

export default function MenuCardLayout({
  item,
  layout,
  enableCart,
  onImageClick,
}: {
  item: MenuItem;
  layout: CardLayout;
  enableCart: boolean;
  onImageClick: (e: React.MouseEvent) => void;
}) {
  return (
    <div
      className="menu-item menu-item-custom"
      id={`menu-${item.id}`}
      style={{ aspectRatio: CARD_ASPECT.menu }}
    >
      {resolveComponents(layout, DEFAULTS).map((component) => (
        <Piece
          key={component.id}
          component={component}
          item={item}
          enableCart={enableCart}
          onImageClick={onImageClick}
        />
      ))}
    </div>
  );
}
