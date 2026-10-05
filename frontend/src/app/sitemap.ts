import { headers } from 'next/headers';
import type { MetadataRoute } from 'next';

/**
 * sitemap.xml.
 *
 * 담는 것은 **우리가 알리려는 페이지**뿐이다 — 랜딩과 기능·요금·도입 절차,
 * 그리고 약관.
 *
 * 매장 메뉴판(`/bid`, `/sorok` …)은 **일부러 넣지 않는다.** 사장님이 QR 을
 * 만든 것은 가게 안 손님에게 보여주기 위해서지 검색에 올리기 위해서가
 * 아니다. 올릴지 말지는 그 매장의 결정이라 우리가 대신 제출하지 않는다.
 * (막지도 않는다 — 링크가 어디에도 없어서 크롤러가 스스로 찾지는 못한다.)
 *
 * 호스트를 보는 이유는 robots.ts 와 같다. develop 은 비운다.
 */
const PRODUCTION_HOST = 'bar-menu.ddnsfree.com';

const PAGES: { path: string; priority: number; changeFrequency: 'weekly' | 'monthly' }[] = [
  { path: '/', priority: 1.0, changeFrequency: 'weekly' },
  { path: '/features', priority: 0.8, changeFrequency: 'monthly' },
  { path: '/pricing', priority: 0.8, changeFrequency: 'monthly' },
  { path: '/guide', priority: 0.6, changeFrequency: 'monthly' },
  { path: '/terms', priority: 0.2, changeFrequency: 'monthly' },
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const host = (await headers()).get('host') ?? '';
  if (host !== PRODUCTION_HOST) return [];

  const lastModified = new Date();
  return PAGES.map((page) => ({
    url: `https://${PRODUCTION_HOST}${page.path}`,
    lastModified,
    changeFrequency: page.changeFrequency,
    priority: page.priority,
  }));
}
