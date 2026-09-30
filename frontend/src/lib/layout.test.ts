import { describe, expect, it } from 'vitest';

import {
  CARD_ASPECT,
  boxStyle,
  isCustomLayout,
  resolveComponents,
  type CardLayout,
  type LayoutComponent,
} from './layout';

/**
 * 저장된 레이아웃을 읽는 규칙.
 *
 * 그동안 이 계약을 Django 테스트가 소스를 문자열로 뒤져서 확인했다. 함수
 * 이름만 바꿔도 통과하는 방식이라, 여기서는 실제로 돌려서 본다.
 *
 * 2026-09-20 적대적 검증에서 망가진 입력 10가지로 손님 화면을 때렸다.
 * 거기서 확인한 성질들을 아래가 못박는다.
 */

const DEFAULTS: LayoutComponent[] = [
  { id: 'category_image', name: '카테고리 이미지', visible: true, x: 0, y: 0, w: 100, h: 65 },
  { id: 'category_name', name: '카테고리명 (한글)', visible: true, x: 5, y: 70, w: 90, h: 15 },
  { id: 'category_name_en', name: '카테고리명 (영문)', visible: true, x: 5, y: 85, w: 90, h: 10 },
];

describe('isCustomLayout — 사장님이 배치를 고쳤는가', () => {
  it('고친 적 없는 매장은 예전 카드로 그린다', () => {
    expect(isCustomLayout({ layout_type: 'default', components: DEFAULTS })).toBe(false);
  });

  it('고친 매장만 절대배치로 그린다', () => {
    expect(isCustomLayout({ layout_type: 'custom', components: DEFAULTS })).toBe(true);
  });

  it('값이 없으면 예전 카드로 그린다', () => {
    expect(isCustomLayout(null)).toBe(false);
    expect(isCustomLayout(undefined)).toBe(false);
  });

  it('components 가 배열이 아니면 예전 카드로 떨어뜨린다', () => {
    // 배열인지 안 보고 .map 을 부르면 그 자리에서 손님 화면이 죽는다.
    const broken = { layout_type: 'custom', components: '없음' } as unknown as CardLayout;
    expect(isCustomLayout(broken)).toBe(false);
  });

  it('components 가 아예 없어도 죽지 않는다', () => {
    const broken = { layout_type: 'custom' } as unknown as CardLayout;
    expect(isCustomLayout(broken)).toBe(false);
  });

  it('layout_type 의 대소문자를 봐준다면 그건 버그다', () => {
    // 빌더는 소문자 'custom' 만 쓴다. 다른 값을 통과시키면 어디서 온
    // 값인지 알 수 없는 배치가 손님 화면에 그려진다.
    expect(isCustomLayout({ layout_type: 'CUSTOM', components: DEFAULTS })).toBe(false);
  });
});

describe('resolveComponents — 무엇을 그릴지 정한다', () => {
  it('저장된 자리가 기본값을 덮는다', () => {
    const layout: CardLayout = {
      layout_type: 'custom',
      components: [{ ...DEFAULTS[1], y: 20, visible: false }],
    };
    const resolved = resolveComponents(layout, DEFAULTS);
    const name = resolved.find((c) => c.id === 'category_name');

    expect(name?.y).toBe(20);
    expect(name?.visible).toBe(false);
  });

  it('저장된 JSON 에 없는 조각은 기본값으로 채운다', () => {
    // 조각이 나중에 늘어날 때, 없는 것을 '숨김' 으로 읽으면 사장님 화면에서
    // 그 조각이 통째로 사라진다. 장바구니 버튼이 정확히 그 경우였다.
    const layout: CardLayout = { layout_type: 'custom', components: [DEFAULTS[0]] };
    const resolved = resolveComponents(layout, DEFAULTS);

    expect(resolved).toHaveLength(3);
    expect(resolved.find((c) => c.id === 'category_name')?.visible).toBe(true);
  });

  it('모르는 id 는 아예 그리지 않는다', () => {
    // 여기가 XSS 를 막는 자리다. 저장값을 돌면 모르는 id 가 화면까지 가지만,
    // 기본값을 돌고 거기 있는 id 만 꺼내면 들어올 자리가 없다.
    const layout = {
      layout_type: 'custom',
      components: [
        { id: '<script>alert(1)</script>', name: 'x', visible: true, x: 0, y: 0, w: 10, h: 10 },
      ],
    } as CardLayout;
    const resolved = resolveComponents(layout, DEFAULTS);

    expect(resolved.map((c) => c.id)).toEqual([
      'category_image',
      'category_name',
      'category_name_en',
    ]);
  });

  it('저장값에 null 이 하나 섞여도 죽지 않는다', () => {
    // admin 의 textarea 가 JSONField 에 그대로 쓰고, 그 필드에는 검증이 없다.
    // components: [null] 하나로 손님 화면이 통째로 에러 화면이 됐다.
    // 2026-09-25 검토에서 실제 손님 화면을 그렇게 만들어 확인했다.
    const layout = { layout_type: 'custom', components: [null] } as unknown as CardLayout;
    expect(() => resolveComponents(layout, DEFAULTS)).not.toThrow();
    expect(resolveComponents(layout, DEFAULTS)).toHaveLength(3);
  });

  it('id 없는 조각도 그냥 건너뛴다', () => {
    const layout = {
      layout_type: 'custom',
      components: [{ visible: true, x: 0, y: 0, w: 10, h: 10 }, DEFAULTS[0]],
    } as unknown as CardLayout;
    expect(resolveComponents(layout, DEFAULTS).map((c) => c.id)).toEqual(DEFAULTS.map((c) => c.id));
  });

  it('순서는 기본값이 정한다', () => {
    const layout: CardLayout = {
      layout_type: 'custom',
      components: [DEFAULTS[2], DEFAULTS[0]],
    };
    expect(resolveComponents(layout, DEFAULTS).map((c) => c.id)).toEqual(DEFAULTS.map((c) => c.id));
  });
});

describe('boxStyle — 조각을 카드 안에 놓는다', () => {
  it('좌표를 % 로 옮긴다', () => {
    expect(boxStyle(DEFAULTS[1])).toMatchObject({
      position: 'absolute',
      left: '5%',
      top: '70%',
      width: '90%',
      height: '15%',
    });
  });

  it('넘치는 내용은 상자 안에서 잘린다', () => {
    // 상자 높이는 사장님이 정한 값이다. 넘친 글자가 아래 조각을 덮으면
    // 빌더에서 본 것과 손님이 보는 것이 달라진다.
    expect(boxStyle(DEFAULTS[1]).overflow).toBe('hidden');
  });
});

describe('CARD_ASPECT — 빌더 캔버스와 같은 비율', () => {
  it('카테고리와 메뉴는 비율이 다르다', () => {
    // 캔버스가 320×240 과 320×440 으로 다르다. 하나로 뭉치면 한쪽이
    // 빌더에서 본 것과 어긋난다.
    expect(CARD_ASPECT.category).not.toBe(CARD_ASPECT.menu);
  });

  it('CSS 가 읽을 수 있는 모양이다', () => {
    for (const value of Object.values(CARD_ASPECT)) {
      expect(value).toMatch(/^\d+ \/ \d+$/);
    }
  });
});
