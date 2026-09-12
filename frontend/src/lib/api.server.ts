/**
 * 서버 컴포넌트가 쓰는 API 클라이언트.
 *
 * 하는 일은 하나다 — 요청에 실려 온 미리보기 토큰을 모든 호출에 자동으로
 * 붙인다. 호출부마다 손으로 넘기게 하면 layout 과 페이지 여러 곳 중 하나는
 * 반드시 빠지고, 빠진 그 화면만 '준비 중' 이 뜬다.
 *
 * 이 파일은 next/headers 를 쓰므로 클라이언트 컴포넌트에서 import 하면
 * 빌드가 깨진다. 검색·장바구니·QR 처럼 브라우저에서 부르는 것들은 계속
 * @/lib/api 를 직접 쓴다 — 그쪽은 이미 공개된 매장에서만 쓰이는 기능이다.
 */

import { headers } from 'next/headers';

import {
  getCategories as getCategoriesRaw,
  getCategoryDetail as getCategoryDetailRaw,
  getCategoryTree as getCategoryTreeRaw,
  getRestaurant as getRestaurantRaw,
} from './api';
import type { Category, CategoryDetail, CategoryTree, RestaurantDetail } from './types';

/**
 * 이번 요청에 실려 온 미리보기 토큰.
 *
 * src/middleware.ts 가 ?preview= 를 x-preview-token 헤더로 옮겨 준다.
 * layout 은 searchParams 를 받지 못하는데 402 를 잡는 곳이 layout 이라,
 * 쿼리를 그대로 읽을 방법이 없기 때문이다.
 */
export async function previewToken(): Promise<string> {
  const headerList = await headers();
  return headerList.get('x-preview-token') || '';
}

export async function getRestaurant(slug: string): Promise<RestaurantDetail> {
  return getRestaurantRaw(slug, await previewToken());
}

export async function getCategories(slug: string): Promise<Category[]> {
  return getCategoriesRaw(slug, await previewToken());
}

export async function getCategoryDetail(slug: string, categoryId: number): Promise<CategoryDetail> {
  return getCategoryDetailRaw(slug, categoryId, await previewToken());
}

export async function getCategoryTree(slug: string): Promise<CategoryTree[]> {
  return getCategoryTreeRaw(slug, await previewToken());
}

export { isMenuClosed } from './api';
