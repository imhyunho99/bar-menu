import type { Metadata } from 'next';

/**
 * 마케팅 페이지의 메타데이터.
 *
 * og:image 를 랜딩에만 달아 두었더니 /pricing·/features 링크를 카톡에 붙이면
 * 썸네일 없이 글자만 떴다. Next 는 부모의 openGraph 를 페이지가 물려받지
 * 않는다(루트 레이아웃엔 없고, 랜딩의 것은 랜딩 페이지 소유다). 그래서 페이지마다
 * 같은 모양으로 채우도록 한 곳에서 만든다.
 *
 * twitter:* 는 Next 가 openGraph 에서 채운다.
 */
const SITE = 'https://bar-menu.ddnsfree.com';

export const OG_IMAGE = {
  // 투명 로고 PNG 를 쓰면 메신저가 흰 칸이나 검은 칸을 띄운다. 1200x630 실사진.
  url: '/marketing/og.jpg',
  width: 1200,
  height: 630,
  alt: '영업 중인 바 카운터',
};

export function marketingMetadata({
  path,
  title,
  description,
  shareDescription = description,
  keywords,
}: {
  path: string;
  title: string;
  description: string;
  /** 공유 카드에 들어갈 문장. 검색 설명보다 짧아야 카드에서 안 잘린다. */
  shareDescription?: string;
  keywords?: string[];
}): Metadata {
  return {
    title,
    description,
    keywords,
    // 같은 페이지가 여러 주소로 잡히면(끝의 / 유무, 쿼리) 평가가 쪼개진다.
    alternates: { canonical: path },
    openGraph: {
      type: 'website',
      url: `${SITE}${path}`,
      siteName: 'bar-menu',
      locale: 'ko_KR',
      title,
      description: shareDescription,
      images: [OG_IMAGE],
    },
  };
}
