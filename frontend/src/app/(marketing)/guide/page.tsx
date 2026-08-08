import Link from 'next/link';
import type { Metadata } from 'next';
import Nav from '@/components/marketing/Nav';
import Footer from '@/components/marketing/Footer';
import { PREP, STEPS } from '@/lib/marketing-content';

export const metadata: Metadata = {
  title: '도입 절차 — bar-menu',
  description:
    '문의부터 오픈까지 다섯 단계. 쓰시던 종이 메뉴판을 찍어 보내주시면 그대로 옮깁니다. 매장에서 준비하실 것은 메뉴판 사진 한 장뿐입니다.',
  alternates: { canonical: '/guide' },
};

export default function GuidePage() {
  return (
    <>
      <Nav active="guide" />

      <header className="wrap mkt-subhero">
        <div className="en">How it works</div>
        <h1 className="kd">
          문의부터 오픈까지
          <br />
          다섯 단계입니다
        </h1>
        <p className="bd">
          매장에서 준비하실 것은 쓰시던 메뉴판 사진 한 장입니다. 옮겨 넣는 일은 저희가 합니다.
        </p>
      </header>

      <div className="wrap">
        <div style={{ paddingTop: 56 }}>
          {STEPS.map((s, i) => (
            <div key={s.h} className="mkt-step reveal">
              <div className="kd num idx">{String(i + 1).padStart(2, '0')}</div>
              <div>
                <h2 className="kd">{s.h}</h2>
                <p className="bd lead">{s.lead}</p>
                <p className="sm">{s.p}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mkt-prep reveal">
          <div>
            <div className="ko-lbl rule-lbl">준비물</div>
            <h2 className="kd">매장에서 준비하실 것</h2>
            <ul>
              {PREP.map((x) => (
                <li key={x}>
                  <span className="dash">—</span>
                  <span>{x}</span>
                </li>
              ))}
            </ul>
            <p className="cap note">
              그 외 서버·도메인·QR 제작·이미지 변환은 모두 포함입니다.
            </p>
          </div>
          <div className="box">
            <div className="ko-lbl">메뉴 입력은 사진 한 장으로 끝납니다</div>
            <p className="sm">
              종이 메뉴판을 찍어 올리면 카테고리와 메뉴를 읽어 그대로 옮깁니다. 한 줄씩 타이핑할
              일이 없습니다.
            </p>
            <p className="sm">
              옮긴 내용은 바로 저장되지 않습니다. 확인 화면에서 같이 보고, 흐리게 찍혀 잘못 읽힌
              곳은 그 자리에서 고친 뒤 저장합니다.
            </p>
            <p className="cap note">
              디자인 조율과 QR 제작·배송은 메뉴 수와 요청에 따라 달라집니다. 문의 주시면 매장
              사정에 맞춰 일정을 잡아 드립니다.
            </p>
          </div>
        </div>

        <div style={{ padding: '56px 0' }} className="reveal">
          <Link href="/#contact" className="btn btn-solid">
            도입 문의하기
          </Link>
        </div>
      </div>

      <Footer />
    </>
  );
}
