/**
 * Django 앱(가입 · 관리자 화면)의 주소.
 *
 * 마케팅 페이지는 Vercel, 앱은 OCI 로 따로 뜬다. 두 쪽을 잇는 주소를 페이지마다
 * 적어두면 develop/운영을 오갈 때 한 군데씩 남는다. 그래서 여기 한 곳에서만 만든다.
 *
 * NEXT_PUBLIC_ 이라 빌드 시점에 값이 박힌다. 환경을 바꾸면 다시 빌드해야 한다.
 */
const APP_ORIGIN = (process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:4311').replace(/\/+$/, '');

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
