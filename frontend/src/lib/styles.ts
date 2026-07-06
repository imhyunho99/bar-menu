import type { SiteSettings } from './types';

/**
 * SiteSettings API 응답을 CSS Custom Properties 문자열로 변환.
 * <style> 태그에 :root { ... } 형태로 주입하여 사용.
 */
export function buildCSSVariables(s: SiteSettings | null): string {
  if (!s) return '';

  const vars: string[] = [];
  const set = (name: string, value: string | number | null | undefined, suffix = '') => {
    if (value !== null && value !== undefined && value !== '') {
      vars.push(`${name}: ${value}${suffix};`);
    }
  };

  // 배경/카드 색상
  set('--bg-color', s.background_color);
  set('--category-card-color', s.category_card_color);
  set('--menu-card-color', s.menu_card_color);

  // 메뉴명(한글)
  set('--menu-name-color', s.menu_name_color);
  set('--menu-name-size', s.menu_name_size, 'px');
  set('--menu-name-weight', s.menu_name_bold ? 'bold' : null);
  set('--menu-name-style', s.menu_name_italic ? 'italic' : null);

  // 메뉴명(영문)
  set('--menu-name-en-color', s.menu_name_en_color);
  set('--menu-name-en-size', s.menu_name_en_size, 'px');
  set('--menu-name-en-weight', s.menu_name_en_bold ? 'bold' : null);
  set('--menu-name-en-style', s.menu_name_en_italic ? 'italic' : null);

  // 가격
  set('--menu-price-color', s.menu_price_color);
  set('--menu-price-size', s.menu_price_size, 'px');
  set('--menu-price-weight', s.menu_price_bold ? 'bold' : null);
  set('--menu-price-style', s.menu_price_italic ? 'italic' : null);

  // 메뉴 설명
  set('--menu-desc-color', s.menu_description_color);
  set('--menu-desc-size', s.menu_description_size, 'px');
  set('--menu-desc-weight', s.menu_description_bold ? 'bold' : null);
  set('--menu-desc-style', s.menu_description_italic ? 'italic' : null);

  // 기타 사항
  set('--menu-notes-color', s.menu_notes_color);
  set('--menu-notes-size', s.menu_notes_size, 'px');
  set('--menu-notes-weight', s.menu_notes_bold ? 'bold' : null);
  set('--menu-notes-style', s.menu_notes_italic ? 'italic' : null);

  // 카테고리명(한글)
  set('--category-name-color', s.category_name_color);
  set('--category-name-size', s.category_name_size, 'px');
  set('--category-name-weight', s.category_name_bold ? 'bold' : null);
  set('--category-name-style', s.category_name_italic ? 'italic' : null);

  // 카테고리명(영문)
  set('--category-name-en-color', s.category_name_en_color);
  set('--category-name-en-size', s.category_name_en_size, 'px');
  set('--category-name-en-weight', s.category_name_en_bold ? 'bold' : null);
  set('--category-name-en-style', s.category_name_en_italic ? 'italic' : null);

  // 페어링명
  set('--pairing-name-color', s.pairing_name_color);
  set('--pairing-name-size', s.pairing_name_size, 'px');
  set('--pairing-name-weight', s.pairing_name_bold ? 'bold' : null);
  set('--pairing-name-style', s.pairing_name_italic ? 'italic' : null);

  // 페어링 설명
  set('--pairing-desc-color', s.pairing_description_color);
  set('--pairing-desc-size', s.pairing_description_size, 'px');
  set('--pairing-desc-weight', s.pairing_description_bold ? 'bold' : null);
  set('--pairing-desc-style', s.pairing_description_italic ? 'italic' : null);

  // 페어링 가격
  set('--pairing-price-color', s.pairing_price_color);
  set('--pairing-price-size', s.pairing_price_size, 'px');
  set('--pairing-price-weight', s.pairing_price_bold ? 'bold' : null);
  set('--pairing-price-style', s.pairing_price_italic ? 'italic' : null);

  const rootRules = `:root { ${vars.join(' ')} }`;

  const overrides: string[] = [];
  const addOverride = (
    selector: string,
    styles: { [key: string]: string | number | boolean | null | undefined },
    unit = ''
  ) => {
    const lines: string[] = [];
    for (const [prop, val] of Object.entries(styles)) {
      if (val !== null && val !== undefined && val !== '') {
        if (typeof val === 'boolean') {
          if (val) {
            if (prop === 'font-weight') lines.push('font-weight: bold !important;');
            if (prop === 'font-style') lines.push('font-style: italic !important;');
          }
        } else {
          // font-size일 때만 unit(px)을 붙이고, color 등에는 붙이지 않음
          const finalUnit = prop === 'font-size' ? unit : '';
          lines.push(`${prop}: ${val}${finalUnit} !important;`);
        }
      }
    }
    if (lines.length > 0) {
      overrides.push(`${selector} { ${lines.join(' ')} }`);
    }
  };

  addOverride('.menu-name-ko', {
    'color': s.menu_name_color,
    'font-size': s.menu_name_size,
    'font-weight': s.menu_name_bold,
    'font-style': s.menu_name_italic,
  }, 'px');

  addOverride('.menu-name-en', {
    'color': s.menu_name_en_color,
    'font-size': s.menu_name_en_size,
    'font-weight': s.menu_name_en_bold,
    'font-style': s.menu_name_en_italic,
  }, 'px');

  addOverride('.menu-price', {
    'color': s.menu_price_color,
    'font-size': s.menu_price_size,
    'font-weight': s.menu_price_bold,
    'font-style': s.menu_price_italic,
  }, 'px');

  addOverride('.menu-description', {
    'color': s.menu_description_color,
    'font-size': s.menu_description_size,
    'font-weight': s.menu_description_bold,
    'font-style': s.menu_description_italic,
  }, 'px');

  addOverride('.menu-notes', {
    'color': s.menu_notes_color,
    'font-size': s.menu_notes_size,
    'font-weight': s.menu_notes_bold,
    'font-style': s.menu_notes_italic,
  }, 'px');

  addOverride('.category-name-ko, .manual-card h3', {
    'color': s.category_name_color,
    'font-size': s.category_name_size,
    'font-weight': s.category_name_bold,
    'font-style': s.category_name_italic,
  }, 'px');

  addOverride('.category-name-en', {
    'color': s.category_name_en_color,
    'font-size': s.category_name_en_size,
    'font-weight': s.category_name_en_bold,
    'font-style': s.category_name_en_italic,
  }, 'px');

  addOverride('.pairing-item-name', {
    'color': s.pairing_name_color,
    'font-size': s.pairing_name_size,
    'font-weight': s.pairing_name_bold,
    'font-style': s.pairing_name_italic,
  }, 'px');

  addOverride('.pairing-item-desc', {
    'color': s.pairing_description_color,
    'font-size': s.pairing_description_size,
    'font-weight': s.pairing_description_bold,
    'font-style': s.pairing_description_italic,
  }, 'px');

  addOverride('.pairing-item-price', {
    'color': s.pairing_price_color,
    'font-size': s.pairing_price_size,
    'font-weight': s.pairing_price_bold,
    'font-style': s.pairing_price_italic,
  }, 'px');

  if (s.menu_card_color) {
    overrides.push(`.menu-item { background-color: ${s.menu_card_color} !important; border-color: ${s.menu_card_color} !important; }`);
  }
  if (s.category_card_color) {
    overrides.push(`.category-card { background-color: ${s.category_card_color} !important; border-color: ${s.category_card_color} !important; }`);
  }

  return `${rootRules}\n${overrides.join('\n')}`;
}

/**
 * SiteSettings의 폰트 파일 URL들을 @font-face 선언으로 변환.
 */
export function buildFontFaces(s: SiteSettings | null): string {
  if (!s) return '';

  const faces: string[] = [];
  const addFont = (family: string, url: string | null) => {
    if (url) {
      faces.push(`@font-face { font-family: '${family}'; src: url('${url}'); font-display: swap; }`);
    }
  };

  addFont('MenuNameFont', s.menu_name_font_url);
  addFont('MenuNameEnFont', s.menu_name_en_font_url);
  addFont('MenuPriceFont', s.menu_price_font_url);
  addFont('MenuDescFont', s.menu_description_font_url);
  addFont('MenuNotesFont', s.menu_notes_font_url);
  addFont('CategoryNameFont', s.category_name_font_url);
  addFont('CategoryNameEnFont', s.category_name_en_font_url);
  addFont('PairingNameFont', s.pairing_name_font_url);
  addFont('PairingDescFont', s.pairing_description_font_url);
  addFont('PairingPriceFont', s.pairing_price_font_url);

  return faces.join('\n');
}
