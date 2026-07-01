// API response types matching Django DRF serializers

export interface Restaurant {
  id: number;
  name: string;
  slug: string;
}

export interface RestaurantDetail extends Restaurant {
  site_settings: SiteSettings | null;
}

export interface SiteSettings {
  logo_image: string | null;
  intro_image: string | null;
  intro_video: string | null;
  loading_video_2: string | null;
  show_manual_card: boolean;
  side_image: string | null;
  background_color: string;
  category_card_color: string;
  menu_card_color: string;
  wifi_ssid: string | null;
  wifi_password: string | null;
  wifi_security: string;
  enable_wifi: boolean;
  enable_payhere: boolean;
  enable_cart: boolean;
  payhere_store_id: string | null;
  restrict_by_ip: boolean;
  store_public_ip: string | null;
  restrict_by_wifi_ssid: boolean;
  disable_screenshots: boolean;
  // 메뉴명(한글)
  menu_name_font_url: string | null;
  menu_name_color: string;
  menu_name_size: number | null;
  menu_name_bold: boolean;
  menu_name_italic: boolean;
  // 메뉴명(영문)
  menu_name_en_font_url: string | null;
  menu_name_en_color: string;
  menu_name_en_size: number | null;
  menu_name_en_bold: boolean;
  menu_name_en_italic: boolean;
  // 가격
  menu_price_font_url: string | null;
  menu_price_color: string;
  menu_price_size: number | null;
  menu_price_bold: boolean;
  menu_price_italic: boolean;
  // 메뉴 설명
  menu_description_font_url: string | null;
  menu_description_color: string;
  menu_description_size: number | null;
  menu_description_bold: boolean;
  menu_description_italic: boolean;
  // 기타 사항
  menu_notes_font_url: string | null;
  menu_notes_color: string;
  menu_notes_size: number | null;
  menu_notes_bold: boolean;
  menu_notes_italic: boolean;
  // 카테고리명(한글)
  category_name_font_url: string | null;
  category_name_color: string;
  category_name_size: number | null;
  category_name_bold: boolean;
  category_name_italic: boolean;
  // 카테고리명(영문)
  category_name_en_font_url: string | null;
  category_name_en_color: string;
  category_name_en_size: number | null;
  category_name_en_bold: boolean;
  category_name_en_italic: boolean;
  // 페어링명
  pairing_name_font_url: string | null;
  pairing_name_color: string;
  pairing_name_size: number | null;
  pairing_name_bold: boolean;
  pairing_name_italic: boolean;
  // 페어링 설명
  pairing_description_font_url: string | null;
  pairing_description_color: string;
  pairing_description_size: number | null;
  pairing_description_bold: boolean;
  pairing_description_italic: boolean;
  // 페어링 가격
  pairing_price_font_url: string | null;
  pairing_price_color: string;
  pairing_price_size: number | null;
  pairing_price_bold: boolean;
  pairing_price_italic: boolean;
}

export interface Category {
  id: number;
  name: string;
  name_en: string | null;
  priority: number;
  parent: number | null;
  category_image: string | null;
  hide_side_image: boolean;
}

export interface CategoryDetail extends Category {
  sub_categories: Category[];
  menu_items: MenuItem[];
  prev_category: { id: number; name: string } | null;
  next_category: { id: number; name: string } | null;
}

export interface CategoryTree extends Category {
  sub_categories: CategoryTree[];
}

export interface MenuItemPairing {
  id: number;
  name: string;
  image: string | null;
  description: string | null;
  price: string | null;
  priority: number;
}

export interface MenuItem {
  id: number;
  name: string;
  name_en: string | null;
  price: string;
  description: string | null;
  notes: string | null;
  menu_image: string | null;
  detail_image: string | null;
  priority: number;
  is_available: boolean;
  display_mode: 'auto' | 'image_only' | 'text_only' | 'combined';
  click_expand: boolean;
  lightbox_style: 'zoom' | 'slide_up' | 'fade';
  lightbox_opacity: number;
  enable_detail_view: boolean;
  detail_description: string | null;
  pairings: MenuItemPairing[];
}

export interface SearchResult {
  type: 'category' | 'menu';
  id: number;
  title: string;
  subtitle: string;
  category_id?: number | null;
}

export interface QRCodeResponse {
  qr_image: string;
  menu_url: string;
}
