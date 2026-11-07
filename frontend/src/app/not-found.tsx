import Link from 'next/link';
import type { Metadata } from 'next';
import Nav from '@/components/marketing/Nav';
import Footer from '@/components/marketing/Footer';
import { mono, myeongjo } from '@/lib/marketing-fonts';
import '@/styles/marketing.css';

/**
 * 없는 주소.
 *
 * 예전에는 Next 기본 화면(흰 바탕에 "404 This page could not be found.")이
 * 떴다. 영어인 데다 갈 곳이 하나도 없어서, 들어온 사람은 뒤로 가기밖에 할 게
 * 없었다.
 *
 * 여기로 오는 사람은 둘이다. 잘못된 링크로 들어온 사장님 후보, 그리고 QR 을
 * 찍었는데 주소가 깨진 매장 손님. 손님에게 영업 페이지를 들이밀 이유는 없으니
 * QR 을 다시 찍으라는 말을 먼저 둔다.
 *
 * 이 파일은 app/ 최상단이라 마케팅 레이아웃 밖이다. 그래서 .mkt 와 폰트를
 * 직접 입힌다.
 */
export const metadata: Metadata = {
  title: '페이지를 찾을 수 없습니다 — bar-menu',
  robots: { index: false },
};

export default function NotFound() {
  return (
    <div className={`mkt ${mono.variable} ${myeongjo.variable}`}>
      <Nav active="none" />

      <header className="wrap mkt-subhero" style={{ borderBottom: 0, paddingBottom: 120 }}>
        <div className="ko-lbl rule-lbl">404</div>
        <h1 className="kd">
          찾으시는 페이지가
          <br />
          없습니다
        </h1>
        <p className="bd" style={{ marginTop: 20 }}>
          주소가 바뀌었거나 잘못 입력된 것 같습니다.
          <br />
          매장 메뉴판을 보시던 중이라면 테이블의 QR 을 한 번 더 찍어 주세요.
        </p>
        <div className="cta-row" style={{ marginTop: 36 }}>
          <Link href="/" className="btn btn-solid">
            처음으로
          </Link>
          <Link href="/#contact" className="btn btn-ghost">
            문의하기
          </Link>
        </div>
      </header>

      <Footer />
    </div>
  );
}
