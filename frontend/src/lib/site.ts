/**
 * Django 앱(가입 · 관리자 화면)의 주소.
 *
 * 마케팅 페이지는 Vercel, 앱은 OCI 로 따로 뜬다. 두 쪽을 잇는 주소를 페이지마다
 * 적어두면 develop/운영을 오갈 때 한 군데씩 남는다. 그래서 여기 한 곳에서만 만든다.
 *
 * NEXT_PUBLIC_ 이라 빌드 시점에 값이 박힌다. 환경을 바꾸면 다시 빌드해야 한다.
 */
const LOCAL_APP_ORIGIN = 'http://localhost:4311';

/**
 * 환경변수가 없으면 배포 빌드를 세운다.
 *
 * 예전에는 조용히 localhost 로 떨어졌다. 그래서 Vercel 에 이 변수를 넣는 걸
 * Preview·Production 두 스코프에서 모두 놓쳤는데도 배포가 초록불이었고,
 * 페이지도 멀쩡해 보였다. 죽은 건 가입 버튼뿐이라 아무도 못 봤다 — 손님이
 * 누르면 자기 컴퓨터의 4311 포트로 갔다.
 *
 * 폴백이 있으면 '설정을 잊었다' 가 '동작하는 것처럼 보인다' 로 바뀐다. 돈이
 * 걸린 경로에서 가장 위험한 실패는 크래시가 아니라 성공한 척이다. 그래서
 * 배포 빌드에서는 폴백을 없애고 빌드를 세운다. 로컬에서 굳이 배포 빌드를
 * 돌려보고 싶으면 값을 명시하면 된다:
 *
 *     NEXT_PUBLIC_APP_URL=http://localhost:4311 npm run build
 */
function resolveAppOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_APP_URL;
  if (configured) return configured.replace(/\/+$/, '');

  // next dev 는 'development'. next build 는 'production' 이라 여기서 갈린다.
  if (process.env.NODE_ENV === 'production') {
    throw new Error(
      'NEXT_PUBLIC_APP_URL 이 없습니다. 이 값이 없으면 모든 가입 버튼이 ' +
        `${LOCAL_APP_ORIGIN} 을 가리킨 채로 배포됩니다.\n` +
        '  Vercel > Settings > Environment Variables 에 스코프별로 넣으세요:\n' +
        '    Production : https://api.bar-menu.ddnsfree.com\n' +
        '    Preview    : https://devapi.bar-menu.ddnsfree.com\n' +
        '  넣은 뒤 반드시 재빌드해야 합니다(NEXT_PUBLIC_ 은 빌드 시점에 박힙니다).',
    );
  }

  return LOCAL_APP_ORIGIN;
}

const APP_ORIGIN = resolveAppOrigin();

/** 앱 안의 경로를 절대 주소로 만든다. 호스트를 아는 유일한 함수다. */
export function appUrl(path = '/'): string {
  return `${APP_ORIGIN}${path.startsWith('/') ? path : `/${path}`}`;
}

/**
 * 셀프 가입 화면. 경로는 backend/menu_project/menu_project/urls.py 의
 * `path('signup/', onboarding_views.signup)` 와 맞춘 것이다.
 */
export const signupUrl = appUrl('/signup/');

/**
 * 요금제를 고른 채로 가입 화면에 들어갈 때.
 *
 * 지금 signup 뷰는 이 파라미터를 읽지 않는다(구독은 항상 Entry 로 생긴다).
 * 그래도 붙여 두는 건 요금표에서 어느 카드를 눌렀는지가 유일하게 남는 흔적이라서다.
 * 뷰가 모르는 쿼리는 그냥 무시되니 지금도 정상 동작한다.
 */
export function signupUrlFor(plan?: string): string {
  return plan ? `${signupUrl}?plan=${encodeURIComponent(plan)}` : signupUrl;
}
