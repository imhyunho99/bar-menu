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

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
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
