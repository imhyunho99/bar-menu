import type { Metadata } from 'next';
import { Analytics } from '@vercel/analytics/next';
import '@/styles/globals.css';

export const metadata: Metadata = {
  // og:image 같은 상대경로를 절대 URL 로 풀어주는 기준점
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'https://bar-menu.ddnsfree.com'),
  title: 'bar-menu | 관리자 맞춤형 스마트 QR 메뉴판 서비스',
  description: '실시간 관리 및 디자인 커스터마이징이 가능한 스마트 QR 메뉴판 솔루션',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
