import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-pathname', request.nextUrl.pathname);

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
}

export const config = {
  matcher: [
    // /_next/ 나 /static 같은 정적 자산을 제외하고 매칭
    '/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)',
  ],
};
