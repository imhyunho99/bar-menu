import Link from 'next/link';
import type { Metadata } from 'next';
import Nav from '@/components/marketing/Nav';
import Footer from '@/components/marketing/Footer';
import { FEATURES } from '@/lib/marketing-content';

export const metadata: Metadata = {
  title: '기능 — bar-menu',
  description:
    '항목별 폰트 커스텀, 드래그 정렬, 이미지 자동 경량화, 주류 페어링, 테이블 주문과 포스 연동, 매장 내 열람 제한까지. bar-menu에서 지금 동작하는 기능 8가지.',
  alternates: { canonical: '/features' },
};

export default function FeaturesPage() {
  return (
    <>
      <Nav active="features" />

      <header className="wrap mkt-subhero">
        <div className="en">Features</div>
        <h1 className="kd">
          메뉴판 하나에
          <br />
          매장 운영이 담깁니다
        </h1>
        <p className="bd">
          디자인부터 주문 접수까지, 실제로 매장에서 쓰이는 기능만 넣었습니다. 아래는 지금 동작하는 기능
          전부입니다.
        </p>
      </header>

      <div className="wrap">
        {FEATURES.map((f, i) => (
          <div key={f.k} className="mkt-feature reveal">
            <div>
              <div className="ko-lbl rule-lbl">{f.k}</div>
              <div className="en-xs">{String(i + 1).padStart(2, '0')}</div>
            </div>
            <div>
              <h2 className="kd">{f.h}</h2>
              <p className="bd">{f.p}</p>
              <ul>
                {f.pts.map((x) => (
                  <li key={x}>
                    <span className="dash">—</span>
                    <span>{x}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}

        <div style={{ padding: '56px 0' }} className="reveal">
          <Link href="/#contact" className="btn btn-solid">
            우리 매장에 맞는지 문의하기
          </Link>
        </div>
      </div>

      <Footer />
    </>
  );
}
