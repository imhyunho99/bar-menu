import { headers } from 'next/headers';
import type { MetadataRoute } from 'next';

/**
 * robots.txt.
 *
 * 없으면 `/robots.txt` 가 `[restaurantSlug]` 라우트로 떨어져 307 로
 * 홈으로 튕긴다. 검색엔진은 그걸 "robots 가 없다"가 아니라 "이상한 응답"으로
 * 받는다 — 2026-10-05 실측에서 실제로 그랬다.
 *
 * 호스트를 보고 정하는 이유: develop.bar-menu 는 같은 코드로 돌지만 색인되면
 * 안 된다. 스테이징이 검색에 뜨면 손님이 거기로 들어가고, 그쪽 데이터는
 * 운영과 다르다. 환경변수로 가르면 develop 쪽에 값을 안 넣었을 때 조용히
 * 운영처럼 굴기 때문에, 요청 호스트를 직접 본다.
 */
const PRODUCTION_HOST = 'bar-menu.ddnsfree.com';

export default async function robots(): Promise<MetadataRoute.Robots> {
  const host = (await headers()).get('host') ?? '';
  const isProduction = host === PRODUCTION_HOST;

  if (!isProduction) {
    return { rules: { userAgent: '*', disallow: '/' } };
  }

  return {
    rules: {
      userAgent: '*',
      allow: '/',
    },
    sitemap: `https://${PRODUCTION_HOST}/sitemap.xml`,
  };
}
