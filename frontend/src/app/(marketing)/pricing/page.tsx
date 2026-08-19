import Link from 'next/link';
import type { Metadata } from 'next';
import Nav from '@/components/marketing/Nav';
import Footer from '@/components/marketing/Footer';
import { COMPARE_ROWS, FAQ, PLANS } from '@/lib/marketing-content';
import { signupUrl, signupUrlFor } from '@/lib/site';

export const metadata: Metadata = {
  title: '요금 — bar-menu',
  description:
    '월 9,900원부터, 부가세 포함. 기기값도 약정도 없고, 가입은 무료입니다. Entry·Pro·Premium 세 요금제에 무엇이 들어가고 무엇이 빠지는지 표로 비교했습니다.',
  alternates: { canonical: '/pricing' },
};

function Mark({ on }: { on: boolean }) {
  return on ? (
    <span className="yes" role="img" aria-label="포함">
      ✓
    </span>
  ) : (
    <span className="no" role="img" aria-label="미포함">
      —
    </span>
  );
}

export default function PricingPage() {
  return (
    <>
      <Nav active="pricing" />

      <header className="wrap mkt-subhero">
        <div className="en">Pricing</div>
        <h1 className="kd">
          기기값도, 약정도
          <br />
          없습니다
        </h1>
        <p className="bd">
          태블릿을 사거나 빌리지 않습니다. 손님 폰이 곧 메뉴판입니다. 가입해서 메뉴를 등록해 보신 뒤에
          결제하시면 되고, 아래 표는 각 요금제에 실제로 포함되는 기능입니다.
        </p>
      </header>

      <div className="wrap">
        <div className="mkt-plans reveal" style={{ paddingTop: 56 }}>
          {PLANS.map((p) => (
            <div key={p.id} className={p.pick ? 'mkt-plan pick' : 'mkt-plan'}>
              {p.pick && <span className="tag">추천 구성</span>}
              <div className="en">{p.name}</div>
              <div className="kd num price">
                {p.price}
                <span className="per">원 / 월</span>
              </div>
              <p className="cap sub" style={{ marginBottom: 28 }}>
                {p.note}
              </p>
              <a href={signupUrlFor(p.id)} className={p.pick ? 'btn btn-solid' : 'btn btn-ghost'}>
                {p.name}로 가입하기
              </a>
            </div>
          ))}
        </div>

        <div className="pt-sec reveal">
          <h2 className="kd" style={{ fontSize: 'clamp(1.5rem,3vw,2.1rem)', marginBottom: 12 }}>
            요금제별 포함 기능
          </h2>
          <p className="bd t-ash" style={{ marginBottom: 32 }}>
            표시된 기능은 모두 지금 동작하는 기능입니다.
          </p>
          {/* 좁은 화면에서 가로로 스크롤된다. tabindex 가 없으면 키보드만 쓰는
              사람은 Pro·Premium 열에 닿지 못한다 */}
          <div className="mkt-table-scroll" tabIndex={0} role="region" aria-label="요금제별 포함 기능 비교표">
            <table className="mkt-table">
              <thead>
                <tr>
                  <th scope="col">기능</th>
                  {PLANS.map((p) => (
                    <th key={p.id} scope="col" className={p.pick ? 'hl' : undefined}>
                      <div className="en">{p.name}</div>
                      <div className="kd num">
                        {p.price}
                        <span className="won">원</span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COMPARE_ROWS.map(([name, a, b, c]) => (
                  <tr key={name}>
                    <th scope="row">{name}</th>
                    <td>
                      <Mark on={a} />
                    </td>
                    <td className="hl">
                      <Mark on={b} />
                    </td>
                    <td>
                      <Mark on={c} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="cap t-ash" style={{ marginTop: 20 }}>
            표시 금액은 모두 부가세 포함입니다. Premium의 초기 디자인비 20만원은 제작이 끝난 뒤에는
            환불되지 않습니다.
          </p>
        </div>

        <div className="pt-sec reveal">
          <h2 className="kd" style={{ fontSize: 'clamp(1.5rem,3vw,2.1rem)', marginBottom: 32 }}>
            자주 묻는 질문
          </h2>
          <div className="mkt-faq">
            {FAQ.map(([q, a]) => (
              <details key={q}>
                <summary>
                  <span className="kd">{q}</span>
                  <span className="plus" aria-hidden="true">
                    +
                  </span>
                </summary>
                <p className="sm">{a}</p>
              </details>
            ))}
          </div>
        </div>

        <div style={{ padding: '56px 0' }} className="reveal">
          <div className="cta-row">
            <a href={signupUrl} className="btn btn-solid">
              무료로 가입하기
            </a>
            <Link href="/#contact" className="btn btn-ghost">
              요금 문의하기
            </Link>
          </div>
          <p className="cap cta-note">
            가입에는 카드가 필요 없습니다. 메뉴를 등록해 확인하신 뒤 결제하시면 손님에게 열립니다.
          </p>
        </div>
      </div>

      <Footer />
    </>
  );
}
