import { notFound } from 'next/navigation';

/**
 * 매장 주소로 쓸 수 있는 모양인가.
 *
 * 백엔드(onboarding_views)가 가입 때 받아주는 글자와 같은 규칙이다.
 * django.urls.converters.SlugConverter 와 같은 글자만 매장이 될 수 있으므로,
 * 여기서 거른 값은 어차피 API 에서 404 가 된다.
 */
const SLUG = /^[a-z0-9][a-z0-9_-]*$/;

/**
 * 매장 주소가 아니면 즉시 404. **API 를 부르기 전에** 끊는다.
 *
 * 왜 필요한가 — `[restaurantSlug]` 는 아무 경로나 다 받는다. 그래서 iOS 가
 * 자동으로 찾는 `/apple-touch-icon.png` 이나 크롤러가 찾는 `/sitemap.txt` 가
 * 전부 "그런 이름의 매장"으로 취급돼 백엔드 API 를 불렀다.
 *
 * 2026-10-06~09 실측: 매장 API 호출 1,725건 중 **160건(9.3%)이 이것**이었고
 * 전부 404 였다. 워커가 둘뿐인 서버라 헛호출 한 건이 진짜 손님의 대기시간이
 * 된다. 점 하나만 봐도 파일 요청인 걸 알 수 있는데 굳이 물어볼 이유가 없다.
 */
export function requireSlugShape(slug: string): void {
  if (!SLUG.test(slug)) notFound();
}
