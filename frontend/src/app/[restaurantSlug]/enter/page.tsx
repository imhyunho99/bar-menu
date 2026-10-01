import { redirect } from 'next/navigation';

/**
 * QR 전용 진입점. 지금은 메뉴판 주소로 넘기기만 한다.
 *
 * 한때 여기서 인트로 영상을 틀었다. 그런데 이 화면은 자체 플레이어를 들고
 * 있었고 1시간 쿨다운(IntroManager 안에 있다)이 따라오지 않아서, 손님이
 * QR 을 찍을 때마다 영상이 처음부터 다시 나왔다. 메뉴를 보다 다시 찍으면
 * 또 나왔다.
 *
 * 영상은 /{slug} 로 되돌렸다. 재생하는 자리가 둘이면 쿨다운도 둘로 갈리고,
 * 갈리면 또 한쪽에서 사라진다. 이 경로는 지우지 않고 남겨 둔다 — 이 주소로
 * 인쇄된 QR 이 돌아다닐 수 있고, 그건 종이라 고칠 수 없다.
 */
export default async function EnterPage({
  params,
}: {
  params: Promise<{ restaurantSlug: string }>;
}) {
  const { restaurantSlug } = await params;
  redirect(`/${restaurantSlug}`);
}
