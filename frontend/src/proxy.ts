import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * 요청이 앱에 닿기 전에 도는 자리.
 *
 * Next 16 에서 middleware 가 proxy 로 이름이 바뀌었다(deprecated). 하는 일은
 * 같고, 파일명과 함수명만 다르다.
 *
 * ── 미리보기 토큰을 들고 다니는 쿠키 ──
 *
 * 사장님은 ?preview=... 가 붙은 링크로 들어오지만, 거기서 카테고리를
 * 누르는 순간 쿼리가 사라진다. 그때 다시 '준비 중' 이 뜨면 미리보기는
 * 첫 화면만 보여주는 기능이 된다.
 *
 * 수명을 토큰과 같은 24시간으로 맞춘다. 쿠키가 더 오래 살아도 토큰이
 * 죽으면 그냥 402 로 떨어지므로 위험하지는 않지만, 죽은 값을 들고 다닐
 * 이유도 없다.
 */
const PREVIEW_COOKIE = 'preview-token';
const PREVIEW_COOKIE_MAX_AGE = 60 * 60 * 24;

export function proxy(request: NextRequest) {
  const fromQuery = request.nextUrl.searchParams.get('preview');
  const token = fromQuery ?? request.cookies.get(PREVIEW_COOKIE)?.value ?? '';

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-pathname', request.nextUrl.pathname);
  // layout 은 searchParams 를 받지 못한다. 402 를 잡는 곳이 layout 이라
  // 미리보기 토큰도 거기서 보여야 해서, 쿼리를 헤더로 옮겨 준다.
  requestHeaders.set('x-preview-token', token);

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  // 주소로 들어온 토큰만 쿠키에 심는다. 쿠키에서 읽은 것을 다시 쓰면
  // 수명이 무한히 연장돼 '하루면 죽는다' 가 거짓이 된다.
  if (fromQuery) {
    response.cookies.set(PREVIEW_COOKIE, fromQuery, {
      maxAge: PREVIEW_COOKIE_MAX_AGE,
      sameSite: 'lax',
      httpOnly: true,
      path: '/',
    });
  }

  return response;
}

export const config = {
  matcher: [
    // /_next/ 나 /static 같은 정적 자산을 제외하고 매칭
    '/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)',
  ],
};
