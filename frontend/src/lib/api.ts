import type {
  Restaurant,
  RestaurantDetail,
  Category,
  CategoryDetail,
  CategoryTree,
  SearchResult,
  QRCodeResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * 상태 코드를 들고 다니는 에러.
 *
 * 결제 전 매장은 402 를 돌려준다. 이걸 그냥 Error 로 뭉개면 호출부가 404 와
 * 구분하지 못해 손님에게 "페이지를 찾을 수 없습니다" 가 뜬다. 가게가 없어진
 * 것처럼 보이는 화면이라, 결제만 하면 열릴 매장에는 쓰면 안 된다.
 */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, statusText: string) {
    super(`API error: ${status} ${statusText}`);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** 아직 열리지 않은 매장인가. 서버의 SubscriptionGateMiddleware 가 402 로 답한다. */
export function isMenuClosed(error: unknown): boolean {
  return error instanceof ApiError && error.status === 402;
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new ApiError(res.status, res.statusText);
  }
  return res.json();
}

// --- Restaurant ---

export async function getRestaurants(): Promise<Restaurant[]> {
  return fetchAPI('/restaurants/');
}

export async function getRestaurant(slug: string): Promise<RestaurantDetail> {
  return fetchAPI(`/restaurants/${slug}/`);
}

// --- Category ---

export async function getCategories(slug: string): Promise<Category[]> {
  return fetchAPI(`/restaurants/${slug}/categories/`);
}

export async function getCategoryDetail(slug: string, categoryId: number): Promise<CategoryDetail> {
  return fetchAPI(`/restaurants/${slug}/categories/${categoryId}/`);
}

export async function getCategoryTree(slug: string): Promise<CategoryTree[]> {
  return fetchAPI(`/restaurants/${slug}/category-tree/`);
}

// --- Search ---

export async function searchMenu(slug: string, query: string): Promise<{ results: SearchResult[] }> {
  return fetchAPI(`/restaurants/${slug}/search/?q=${encodeURIComponent(query)}`);
}

// --- QR Code ---

export async function getQRCode(slug: string, baseUrl?: string): Promise<QRCodeResponse> {
  const params = baseUrl ? `?base_url=${encodeURIComponent(baseUrl)}` : '';
  return fetchAPI(`/restaurants/${slug}/qr/${params}`);
}

// --- Contact ---

export async function submitContact(data: { name: string; contact_info: string; plan: string }): Promise<{ status: string; message: string }> {
  return fetchAPI('/contact/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// --- Order ---

export async function createOrder(slug: string, data: { table_number: string; items: { menu_item: number; quantity: number }[] }): Promise<any> {
  return fetchAPI(`/restaurants/${slug}/orders/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
