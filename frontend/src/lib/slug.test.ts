import { describe, it, expect, vi, beforeEach } from 'vitest';

/**
 * `[restaurantSlug]` 는 아무 경로나 다 받는다. 그래서 iOS 가 자동으로 찾는
 * /apple-touch-icon.png 이나 크롤러가 찾는 /sitemap.txt 가 "그런 이름의 매장"
 * 으로 취급돼 백엔드 API 를 불렀다.
 *
 * 2026-10-06~09 실측: 매장 API 호출 1,725건 중 160건(9.3%)이 이것이었고 전부
 * 404 였다. 워커가 둘뿐인 서버라 헛호출 한 건이 진짜 손님의 대기시간이 된다.
 *
 * 가짜 notFound 는 **던지지 않는다.** 진짜 Next 의 notFound() 는 던지지만,
 * 여기서 던지게 해 두면 그 예외가 테스트 밖으로 새어 파일 전체가 빨간불이
 * 된다(실제로 그랬다). 여기서 볼 것은 "불렀는가" 하나뿐이다.
 */
const { notFound } = vi.hoisted(() => ({ notFound: vi.fn() }));
vi.mock('next/navigation', () => ({ notFound }));

const { requireSlugShape } = await import('./slug');

beforeEach(() => notFound.mockClear());

describe('매장 주소 모양 검사', () => {
  it.each([
    'apple-touch-icon.png',
    'apple-touch-icon-precomposed.png',
    'apple-touch-icon-120x120.png',
    'sitemap.txt',
    'robots.txt',
    '.env',
    '.git',
    'favicon.ico',
    'wp-config.php',
    'Bid',
    '-bar',
    '',
  ])('%s 은 API 를 부르기 전에 404 로 끊는다', (path) => {
    requireSlugShape(path);
    expect(notFound).toHaveBeenCalledOnce();
  });

  it.each(['bid', 'sorok', 'test', 'bar-menu', 'a1', 'my_bar'])(
    '진짜 매장 주소 %s 는 통과한다',
    (slug) => {
      requireSlugShape(slug);
      expect(notFound).not.toHaveBeenCalled();
    },
  );
});
