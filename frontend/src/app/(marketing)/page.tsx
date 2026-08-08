import Image from 'next/image';
import Link from 'next/link';
import type { Metadata } from 'next';
import Nav from '@/components/marketing/Nav';
import Footer from '@/components/marketing/Footer';
import ContactSection from '@/components/marketing/ContactSection';
import { PLANS } from '@/lib/marketing-content';
import { signupUrl, signupUrlFor } from '@/lib/site';

export const metadata: Metadata = {
  title: 'bar-menu | 바·이자카야를 위한 QR 메뉴판',
  description:
    '손님이 QR을 찍으면 매장의 폰트와 색으로 메뉴판이 열립니다. 메뉴가 바뀌면 사장님이 그 자리에서 고칩니다. 카드 등록 없이 14일 무료 체험, 태블릿도 약정도 없이 월 9,900원부터.',
  keywords: ['QR 메뉴판', '스마트 메뉴판', '모바일 메뉴판', '테이블 오더', '바 메뉴판', '이자카야 메뉴판'],
  openGraph: {
    type: 'website',
    url: 'https://bar-menu.ddnsfree.com/',
    title: 'bar-menu | 바·이자카야를 위한 QR 메뉴판',
    description: '매장의 폰트와 색으로 열리는 QR 메뉴판. 메뉴 변경은 사장님이 그 자리에서.',
    images: [{ url: '/marketing/logo-t.png' }],
  },
};

const FACTS = [
  { n: '9,900', u: '원', label: '월 구독', sub: '가장 낮은 요금제 · VAT 포함' },
  { n: '0', u: '원', label: '기기값 · 설치비', sub: '태블릿을 사지 않습니다' },
  { n: '무약정', u: '', label: '약정 없음', sub: '언제든 해지' },
  { n: '5', u: '분', label: '배우면 끝', sub: '어드민 사용법' },
];

const PHOTOCARDS = [
  {
    src: '/marketing/card-cocktails.jpg',
    alt: '바 카운터 위에 놓인 칵테일 세 잔',
    kicker: '디자인',
    h: '폰트와 색을 매장에 맞춥니다',
    p: '매장이 쓰는 폰트를 그대로 올리고 배경을 조도에 맞춰 어둡게. 손님 손 안에서도 우리 매장입니다.',
  },
  {
    src: '/marketing/card-whisky.jpg',
    alt: '잔에 따르고 있는 위스키',
    kicker: '매출',
    h: '안주를 열면 술이 따라옵니다',
    p: '메뉴마다 어울리는 술을 아래에 붙여 보여줍니다. 묻지 않아도 한 잔이 더 나갑니다.',
  },
];

const ADMIN_POINTS = [
  ['끌어서 옮기기', '오늘 밀고 싶은 메뉴를 맨 위로. 끌어 놓으면 그대로 손님 화면입니다.'],
  ['토글 하나로 감추기', '재료가 떨어지면 그 자리에서 끕니다. 없는 메뉴로 사과할 일이 없어집니다.'],
  ['사진은 올리기만', '자동으로 가벼워집니다. 신호가 약한 지하에서도 화면이 먼저 뜹니다.'],
];

const TRADES = ['이자카야', '와인바', '요리주점', '다이닝바', '크래프트 펍', '포차'];

/** 손님 화면 목업. 안에 든 것은 실제 서비스 스크린샷이다. */
function Phone({ small = false }: { small?: boolean }) {
  return (
    <div className={small ? 'phone phone-sm' : 'phone'}>
      <div className="screen">
        <Image
          src="/marketing/menu.jpg"
          alt="손님 휴대폰에 열린 메뉴판 실제 화면"
          width={390}
          height={844}
          sizes="290px"
        />
      </div>
    </div>
  );
}

function Shot({ src, alt, badge }: { src: string; alt: string; badge: string }) {
  const size = src.includes('drag') ? { w: 860, h: 360 } : { w: 810, h: 340 };
  return (
    <div className="mkt-shot">
      <Image src={src} alt={alt} width={size.w} height={size.h} sizes="(min-width:1024px) 620px, 100vw" />
      <span className="badge">{badge}</span>
    </div>
  );
}

export default function LandingPage() {
  // 근거 없는 별점·리뷰 수를 넣었던 구조화 데이터를 걷어내고 실제 가격만 남긴다
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'bar-menu',
    operatingSystem: 'All',
    applicationCategory: 'BusinessApplication',
    offers: {
      '@type': 'Offer',
      price: '9900',
      priceCurrency: 'KRW',
      description: '월 구독 (부가세 포함)',
    },
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />

      <Nav />

      <header className="wrap mkt-hero rise">
        <div className="en">Izakaya · Wine Bar · Gastro Pub</div>
        <h1 className="kd">
          메뉴가 바뀔 때마다
          <br />
          <span className="acc struck">인쇄소</span>에 맡기지 않습니다
        </h1>
        <div className="row">
          <p className="lede">
            손님이 QR을 찍으면 매장의 폰트와 색으로 메뉴판이 열립니다. 메뉴가 바뀌면 사장님이 그 자리에서
            고칩니다. 저장 버튼도, 인쇄 대기도 없습니다.
          </p>
          <div className="cta">
            <a href={signupUrl} className="btn btn-solid">
              14일 무료로 시작하기
            </a>
            <a href="#how" className="btn btn-ghost">
              어떻게 쓰는지 보기
            </a>
            <p className="cap cta-note">
              카드를 등록하지 않습니다. 먼저 이야기부터 나누고 싶으시면{' '}
              <a href="#contact">문의를 남겨주세요</a>.
            </p>
          </div>
        </div>
      </header>

      <section className="mkt-stage">
        <div className="photo grain">
          <Image
            src="/marketing/hero-bar.jpg"
            alt="영업 중인 바 카운터"
            width={2000}
            height={1500}
            sizes="100vw"
            priority
          />
        </div>
        <div className="copy">
          <div className="wrap">
            <div className="box">
              <div className="ko-lbl live">지금 운영 중</div>
              <p className="lead">
                공들여 만든 매장 분위기가
                <br />흰 화면과 기본 폰트에서 끊기지 않게.
              </p>
              <p className="sm sub">오른쪽은 손님 테이블에서 실제로 열리는 화면입니다.</p>
            </div>
          </div>
        </div>
        <div className="phone-slot phsh">
          <Phone />
        </div>
      </section>

      <div className="wrap mt-stage">
        <div className="mkt-facts reveal">
          {FACTS.map((f) => (
            <div key={f.label}>
              <div className="kd num n">
                {f.n}
                <span className="u">{f.u}</span>
              </div>
              <div className="ko-lbl">{f.label}</div>
              <div className="cap">{f.sub}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="wrap pt-sec" id="how">
        <div className="sec-head reveal">
          <div className="ko-lbl rule-lbl">사용</div>
          <h2 className="kd">사장님이 직접 만집니다</h2>
          <p className="bd">고치면 손님 화면에 바로 반영됩니다. 저장 버튼이 없습니다.</p>
        </div>

        <div className="mkt-photocards" style={{ marginTop: 56 }}>
          {PHOTOCARDS.map((c) => (
            <div key={c.kicker} className="mkt-photocard reveal">
              <Image
                src={c.src}
                alt={c.alt}
                width={1400}
                height={1085}
                sizes="(min-width:768px) 50vw, 100vw"
              />
              <div className="veil" />
              <div className="body">
                <div className="ko-lbl rule-lbl">{c.kicker}</div>
                <h3 className="kd">{c.h}</h3>
                <p className="sm">{c.p}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mkt-admin reveal">
          <div className="shots">
            <div>
              <Shot
                src="/marketing/admin-drag.jpg"
                alt="카테고리 행을 끌어 순서를 바꾸는 중인 관리자 화면"
                badge="끌어서 이동 중"
              />
              <p className="cap">
                행 왼쪽 <span className="t-ink">⠿</span> 를 잡고 끌면 손님 화면의 순서가 그대로 바뀝니다.
              </p>
            </div>
            <div>
              <Shot
                src="/marketing/admin-soldout.jpg"
                alt="메뉴 상태가 판매중과 품절로 표시된 관리자 화면"
                badge="품절 처리"
              />
              <p className="cap">
                재료가 떨어진 메뉴만 <span className="t-ink">품절</span>로 바꿉니다. 손님 화면에서 즉시
                사라집니다.
              </p>
            </div>
          </div>
          <div>
            <div className="ko-lbl rule-lbl">어드민</div>
            <h3 className="kd">배우는 데 5분이면 됩니다</h3>
            <p className="bd t-ash" style={{ marginBottom: 36 }}>
              복잡한 설정 화면이 아닙니다. 끌어서 옮기고, 눌러서 끄면 끝입니다.
            </p>
            <div className="points">
              {ADMIN_POINTS.map(([h, p]) => (
                <div key={h} className="point">
                  <h4 className="kd">{h}</h4>
                  <p className="sm">{p}</p>
                </div>
              ))}
            </div>
            <p className="cap note">화면은 데모 매장 기준입니다. 실제 매장 데이터는 담겨 있지 않습니다.</p>
          </div>
        </div>

        <div className="mkt-mirror reveal">
          <div className="cols">
            <div className="col">
              <div className="ko-lbl rule-lbl">사장님 화면</div>
              <h4 className="kd">여기서 끄면</h4>
              <Shot
                src="/marketing/admin-soldout.jpg"
                alt="관리자 화면에서 메뉴를 품절로 표시한 상태"
                badge="품절"
              />
            </div>
            <div className="col">
              <div className="ko-lbl rule-lbl">손님 화면</div>
              <h4 className="kd">여기서 사라집니다</h4>
              <div className="phone-wrap">
                <Phone small />
              </div>
            </div>
          </div>
          <p className="cap foot">저장 버튼이 없습니다. 바꾸는 즉시 손님이 보는 화면에 반영됩니다.</p>
        </div>

        <div style={{ marginTop: 36 }} className="reveal">
          <Link href="/features" className="btn-under">
            기능 8가지 자세히 보기 <span aria-hidden="true">→</span>
          </Link>
        </div>
      </div>

      <section className="mkt-marquee mt-sec" aria-hidden="true">
        <div className="track">
          {[0, 1].map((i) => (
            <div className="grp" key={i}>
              {TRADES.map((t) => (
                <span key={t} style={{ display: 'contents' }}>
                  <span className="acc item">{t}</span>
                  <span className="dot">✳</span>
                </span>
              ))}
            </div>
          ))}
        </div>
      </section>

      <div className="wrap pt-sec">
        <div className="sec-head reveal">
          <div className="ko-lbl rule-lbl">요금</div>
          <h2 className="kd">태블릿을 사거나 빌리지 않습니다</h2>
          <p className="bd">
            손님 폰이 곧 메뉴판입니다. 약정도 없습니다. 표시 금액은 부가세 포함이고, 어느 요금제든 14일
            무료 체험으로 먼저 써보실 수 있습니다.
          </p>
        </div>

        <div className="mkt-plans" style={{ marginTop: 56 }}>
          {PLANS.map((p) => (
            <div key={p.id} className={p.pick ? 'mkt-plan pick reveal' : 'mkt-plan reveal'}>
              {p.pick && <span className="tag">추천 구성</span>}
              <div className="en">{p.name}</div>
              <div className="kd num price">
                {p.price}
                <span className="per">원 / 월</span>
              </div>
              <p className="cap sub">{p.note}</p>
              <ul>
                {p.items.map((x, i) => (
                  <li key={x}>
                    <span className="dash">—</span>
                    <span className={i === 0 && p.pick ? 't-ink' : undefined} style={i === 0 && p.pick ? { fontWeight: 600 } : undefined}>
                      {x}
                    </span>
                  </li>
                ))}
              </ul>
              <a href={signupUrlFor(p.id)} className={p.pick ? 'btn btn-solid' : 'btn btn-ghost'}>
                무료로 시작하기
              </a>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 36, textAlign: 'center' }} className="reveal">
          <Link href="/pricing" className="btn-under">
            요금제별 포함 기능 전부 보기 <span aria-hidden="true">→</span>
          </Link>
        </div>
      </div>

      <div className="wrap pt-sec">
        <div className="mkt-more reveal">
          <div className="ko-lbl rule-lbl">더 자세히</div>
          <div className="grid">
            <Link href="/features">
              <h3 className="kd">
                기능 전체 보기
                <span className="arw" aria-hidden="true">
                  →
                </span>
              </h3>
              <p className="sm">
                항목별 폰트 커스텀부터 포스 연동까지, 지금 동작하는 기능 8가지를 하나씩 설명합니다.
              </p>
            </Link>
            <Link href="/pricing">
              <h3 className="kd">
                요금제 자세히
                <span className="arw" aria-hidden="true">
                  →
                </span>
              </h3>
              <p className="sm">
                세 요금제에 무엇이 들어가고 무엇이 빠지는지 표로 비교하고, 자주 묻는 질문에 답합니다.
              </p>
            </Link>
            <Link href="/guide">
              <h3 className="kd">
                도입 절차
                <span className="arw" aria-hidden="true">
                  →
                </span>
              </h3>
              <p className="sm">
                가입부터 오픈까지 다섯 단계. 쓰시던 메뉴판을 찍어 올리면 읽어서 옮기고, 확인한 뒤
                저장합니다.
              </p>
            </Link>
          </div>
        </div>
      </div>

      <div className="mt-sec">
        <ContactSection />
      </div>
      <Footer />
    </>
  );
}
