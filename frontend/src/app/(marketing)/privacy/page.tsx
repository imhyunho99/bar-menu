import Link from 'next/link';
import type { Metadata } from 'next';
import { marketingMetadata } from '@/lib/marketing-meta';
import { SUPPORT_EMAIL, SUPPORT_PHONE } from '@/lib/business';
import Nav from '@/components/marketing/Nav';
import Footer from '@/components/marketing/Footer';

/**
 * 개인정보 처리방침.
 *
 * 여기 적힌 것은 전부 코드와 서버에서 확인한 사실이다(2026-11-07).
 * 받는 항목·보내는 곳을 바꾸면 이 페이지도 같이 고쳐야 한다. 처리방침과 실제가
 * 어긋나면 그 자체로 법 위반이다.
 *
 *   가입        menu/onboarding_views.py   이메일·비밀번호·매장명·주소·연락처(선택)
 *   문의        ContactSubmission          매장명·연락처·관심 요금제
 *   입금 확인   PaymentRequest             입금자명·입금액·요금제
 *   알림        menu/notifications.py      Discord 로 매장명·이메일·연락처
 *   오류        settings.py sentry_sdk     send_default_pii=False, EU 리전
 *   서버        OCI ap-chuncheon-1         nginx 접속 기록 logrotate 14일
 *   손님 화면   개인정보를 받지 않는다. 주문은 테이블 번호와 메뉴뿐이다.
 */

export const metadata: Metadata = marketingMetadata({
  path: '/privacy',
  title: '개인정보 처리방침 — bar-menu',
  description: 'bar-menu가 어떤 개인정보를 왜 받고, 얼마나 보관하며, 누구에게 맡기는지 적었습니다.',
});

type Row = { t: string; d: string };

const COLLECT: Row[] = [
  {
    t: '회원가입 (사장님)',
    d: '필수: 이메일(아이디로 씁니다), 비밀번호, 매장명, 메뉴판 주소로 쓸 영문 이름. 선택: 연락처. 비밀번호는 되돌릴 수 없는 방식으로 암호화해 저장하며 운영자도 볼 수 없습니다.',
  },
  {
    t: '도입 문의',
    d: '매장명, 연락처 또는 이메일, 관심 요금제.',
  },
  {
    t: '요금 입금 확인',
    d: '입금자명, 입금액, 선택한 요금제.',
  },
  {
    t: '서비스 이용 중 자동으로 남는 것',
    d: '접속 IP 주소, 접속 일시, 브라우저 정보, 오류 기록. 매장 와이파이 접속 제한 기능을 켜면 매장의 공인 IP 주소를 저장합니다.',
  },
  {
    t: '손님 (메뉴판을 보는 분)',
    d: '이름·연락처 등 개인정보를 받지 않습니다. 주문 기능을 쓰는 매장에서는 테이블 번호와 주문한 메뉴만 저장합니다. 방문 통계는 개인을 알아볼 수 없는 집계 형태로만 남습니다.',
  },
];

const PURPOSE: string[] = [
  '계정을 만들고 메뉴판·관리자 화면을 제공하기 위해',
  '도입 문의에 답하고 상담하기 위해',
  '요금 입금을 확인하고, 체험·구독 만료를 미리 알려드리기 위해',
  '장애를 찾아 고치고, 부정 이용을 막아 서비스를 안전하게 운영하기 위해',
];

const RETAIN: Row[] = [
  { t: '회원 정보', d: '회원 탈퇴 시까지. 탈퇴하시면 지체 없이 파기합니다.' },
  { t: '도입 문의', d: '접수일로부터 1년. 그 사이 가입하시면 회원 정보로 이어집니다.' },
  { t: '서버 접속 기록', d: '최대 14일 보관 후 자동 삭제합니다.' },
  { t: '오류 기록', d: '최대 90일 보관 후 자동 삭제합니다.' },
];

const LAW_RETAIN: Row[] = [
  { t: '계약 또는 청약철회에 관한 기록', d: '5년 (전자상거래 등에서의 소비자보호에 관한 법률)' },
  { t: '대금 결제 및 재화 등의 공급에 관한 기록', d: '5년 (같은 법)' },
  { t: '소비자의 불만 또는 분쟁 처리에 관한 기록', d: '3년 (같은 법)' },
];

const TRUSTEES: Row[] = [
  {
    t: 'Oracle Corporation — Oracle Cloud',
    d: '서버 운영과 데이터 보관. 데이터는 대한민국(춘천) 데이터센터에 저장됩니다.',
  },
  {
    t: 'Vercel Inc.',
    d: '웹사이트 전송과 방문 통계. 방문 통계는 쿠키를 쓰지 않고 개인을 식별하지 않습니다.',
  },
  {
    t: 'Discord Inc.',
    d: '문의·가입·입금 확인 신청이 들어왔을 때 운영자에게 보내는 알림. 매장명, 이메일, 연락처가 담깁니다.',
  },
  {
    t: 'Functional Software, Inc. — Sentry',
    d: '오류 기록 수집. 이름·이메일 등 개인 식별 정보는 보내지 않도록 설정했습니다.',
  },
];

const ABROAD: Row[] = [
  {
    t: 'Vercel Inc. — 미국',
    d: '항목: 접속 IP, 브라우저 정보 · 목적: 웹사이트 전송, 방문 통계 · 보유: 전송 즉시 또는 통계 집계 후 파기',
  },
  {
    t: 'Discord Inc. — 미국',
    d: '항목: 매장명, 이메일, 연락처 · 목적: 운영자 알림 · 보유: 알림 처리 후 1년 이내 삭제',
  },
  {
    t: 'Functional Software, Inc. (Sentry) — 독일(EU 리전)',
    d: '항목: 오류 기록, 브라우저 정보 · 목적: 장애 대응 · 보유: 최대 90일',
  },
];

const COOKIES: Row[] = [
  { t: '로그인 유지', d: '관리자 화면에 로그인한 상태를 최대 2주 동안 유지합니다. 로그아웃하면 바로 사라집니다.' },
  { t: '보안', d: '다른 사이트가 사장님 대신 요청을 보내지 못하게 막습니다.' },
  { t: '미리보기', d: '결제 전 메뉴판을 미리 볼 때 24시간 동안 미리보기 상태를 유지합니다.' },
];

const REMEDIES: Row[] = [
  { t: '개인정보침해신고센터', d: '국번 없이 118 · privacy.kisa.or.kr' },
  { t: '개인정보분쟁조정위원회', d: '1833-6972 · kopico.go.kr' },
  { t: '대검찰청', d: '국번 없이 1301 · spo.go.kr' },
  { t: '경찰청', d: '국번 없이 182 · ecrm.police.go.kr' },
];

function Defs({ items }: { items: Row[] }) {
  return (
    <dl className="defs">
      {items.map((x) => (
        <div key={x.t}>
          <dt className="ko-lbl">{x.t}</dt>
          <dd className="sm">{x.d}</dd>
        </div>
      ))}
    </dl>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="bullets">
      {items.map((x) => (
        <li key={x} className="sm">
          <span className="dash" aria-hidden="true">
            —
          </span>
          <span>{x}</span>
        </li>
      ))}
    </ul>
  );
}

/** 연락 창구. 사업자 정보에 이메일·전화가 채워지면 그걸 쓰고, 없으면 문의 양식. */
function ContactLine() {
  const channels = [SUPPORT_EMAIL && `이메일 ${SUPPORT_EMAIL}`, SUPPORT_PHONE && `전화 ${SUPPORT_PHONE}`].filter(
    Boolean,
  );
  return (
    <p className="sm">
      개인정보 보호책임자: 나현호 (대표)
      <br />
      연락: {channels.length > 0 && <>{channels.join(' · ')} · </>}
      <Link href="/#contact" className="t-ink">
        문의 양식
      </Link>{' '}
      (보통 10분 안팎으로 답장드립니다)
    </p>
  );
}

export default function PrivacyPage() {
  return (
    <>
      <Nav active="none" />

      <header className="wrap mkt-subhero">
        <div className="ko-lbl rule-lbl">개인정보 처리방침</div>
        <h1 className="kd">
          받는 것은 적게,
          <br />
          받은 것은 적어 둡니다
        </h1>
        <p className="bd">2026년 11월 7일 공개 · 같은 날 시행</p>
      </header>

      <div className="wrap mkt-legal">
        <section>
          <h2 className="kd">제1조 (받는 개인정보)</h2>
          <p className="sm">
            bar-menu(이하 &lsquo;회사&rsquo;)는 서비스에 꼭 필요한 정보만 받습니다. 14세 미만 아동의
            개인정보는 받지 않습니다.
          </p>
          <Defs items={COLLECT} />
        </section>

        <section>
          <h2 className="kd">제2조 (쓰는 목적)</h2>
          <Bullets items={PURPOSE} />
          <p className="sm">목적이 바뀌면 미리 알리고, 필요한 경우 다시 동의를 받습니다.</p>
        </section>

        <section>
          <h2 className="kd">제3조 (보관 기간과 파기)</h2>
          <Defs items={RETAIN} />
          <p className="sm">법에서 정한 기록은 아래 기간 동안 따로 보관한 뒤 파기합니다.</p>
          <Defs items={LAW_RETAIN} />
          <p className="sm">
            파기할 때 전자 파일은 복구할 수 없는 방법으로 지우고, 종이 문서는 분쇄하거나 소각합니다.
          </p>
        </section>

        <section>
          <h2 className="kd">제4조 (제3자 제공)</h2>
          <p className="sm">
            회사는 개인정보를 제3자에게 팔거나 넘기지 않습니다. 법령에 따라 수사기관 등이 정해진 절차로
            요구하는 경우에만 예외로 합니다.
          </p>
        </section>

        <section>
          <h2 className="kd">제5조 (처리 위탁)</h2>
          <p className="sm">서비스 운영을 위해 아래 업체에 처리를 맡깁니다.</p>
          <Defs items={TRUSTEES} />
        </section>

        <section>
          <h2 className="kd">제6조 (국외 이전)</h2>
          <p className="sm">
            위 업체 중 일부는 해외에서 정보를 처리합니다. 서비스를 이용하실 때 네트워크로 전송되며,
            이전을 원하지 않으시면 회원가입과 문의를 하지 않으시면 됩니다. 이 경우 서비스 이용이
            어렵습니다.
          </p>
          <Defs items={ABROAD} />
        </section>

        <section>
          <h2 className="kd">제7조 (쿠키)</h2>
          <p className="sm">광고나 추적을 위한 쿠키는 쓰지 않습니다. 쓰는 것은 아래 세 가지뿐입니다.</p>
          <Defs items={COOKIES} />
          <p className="sm">브라우저 설정에서 쿠키를 막을 수 있지만, 그러면 관리자 화면에 로그인할 수 없습니다.</p>
        </section>

        <section>
          <h2 className="kd">제8조 (정보주체의 권리)</h2>
          <p className="sm">
            언제든 내 개인정보를 열람하거나 고치거나 지워 달라고, 또는 처리를 멈춰 달라고 요청하실 수
            있습니다. 아래 창구로 알려 주시면 본인 확인 후 지체 없이 처리합니다. 회원 탈퇴도 같은
            창구로 요청하시면 됩니다.
          </p>
        </section>

        <section>
          <h2 className="kd">제9조 (안전하게 지키는 방법)</h2>
          <Bullets
            items={[
              '비밀번호는 되돌릴 수 없는 방식으로 암호화해 저장합니다.',
              '모든 통신은 HTTPS로 암호화합니다.',
              '관리자 화면은 매장마다 분리되어, 다른 매장의 정보에 접근할 수 없습니다.',
              '개인정보를 다루는 사람을 최소한으로 제한합니다.',
            ]}
          />
        </section>

        <section>
          <h2 className="kd">제10조 (보호책임자와 문의)</h2>
          <ContactLine />
          <p className="sm">침해를 신고하거나 상담이 필요하시면 아래 기관에도 문의하실 수 있습니다.</p>
          <Defs items={REMEDIES} />
        </section>

        <section>
          <h2 className="kd">제11조 (변경)</h2>
          <p className="sm">
            이 방침을 바꾸면 시행 7일 전부터 이 페이지에 알립니다. 받는 항목이 늘어나는 등 중요한
            변경은 30일 전에 알립니다.
          </p>
        </section>
      </div>

      <Footer />
    </>
  );
}
