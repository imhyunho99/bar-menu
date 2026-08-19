import Link from 'next/link';
import type { Metadata } from 'next';
import Nav from '@/components/marketing/Nav';
import Footer from '@/components/marketing/Footer';
import { PREP, STEPS } from '@/lib/marketing-content';
import { signupUrl } from '@/lib/site';

export const metadata: Metadata = {
  title: '도입 절차 — bar-menu',
  description:
    '가입부터 오픈까지 다섯 단계. 쓰시던 종이 메뉴판을 찍어 올리면 읽어서 옮기고, 확인한 뒤 저장합니다. 가입은 무료이고, 결제하면 손님에게 열립니다.',
  alternates: { canonical: '/guide' },
};

export default function GuidePage() {
  return (
    <>
      <Nav active="guide" />

      <header className="wrap mkt-subhero">
        <div className="en">How it works</div>
        <h1 className="kd">
          가입부터 오픈까지
          <br />
          다섯 단계입니다
        </h1>
        <p className="bd">
          회신을 기다리는 단계가 없습니다. 매장에서 준비하실 것은 쓰시던 메뉴판 사진 한 장이고, 옮겨 넣는
          일은 사진을 읽어 대신 합니다.
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
              그 외 서버·도메인·QR 생성·이미지 변환은 모두 포함입니다.
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
              중간에 사람을 기다리는 단계는 없습니다. 가입도, 메뉴 등록도, QR 인쇄도 사장님이 그
              자리에서 하십니다. 다만 Pro 이상의 아크릴 거치대는 물건이라 우편으로 따로 가고, 그
              전까지는 인쇄한 QR로 여시면 됩니다.
            </p>
          </div>
        </div>

        <div style={{ padding: '56px 0' }} className="reveal">
          <div className="cta-row">
            <a href={signupUrl} className="btn btn-solid">
              무료로 가입하기
            </a>
            <Link href="/#contact" className="btn btn-ghost">
              먼저 상담받기
            </Link>
          </div>
          <p className="cap cta-note">
            카드를 등록하지 않습니다. 가입이 끝나면 바로 로그인된 채로 할 일 목록이 열리고, 첫 항목이
            메뉴 등록입니다.
          </p>
        </div>
      </div>

      <Footer />
    </>
  );
}
