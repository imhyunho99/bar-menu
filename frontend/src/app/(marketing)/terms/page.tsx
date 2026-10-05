import type { Metadata } from 'next';
import Nav from '@/components/marketing/Nav';
import Footer from '@/components/marketing/Footer';

/**
 * 이용약관.
 *
 * 예전에는 `app/terms/` 에 홀로 있으면서 인라인 <style> 로 body 를 통째로
 * 어둡게 칠하고 구글 폰트를 따로 불러왔다. 그래서 랜딩과 전혀 다른 화면이
 * 나왔고, Nav 도 없었다. `(marketing)` 안으로 옮겨 레이아웃·폰트·디자인
 * 시스템을 그대로 쓴다. 주소는 그대로 /terms 다 — 라우트 그룹은 URL 에
 * 나타나지 않는다.
 *
 * 조항의 효력 있는 내용(금액·기간·의무)은 바꾸지 않았다. 바꾼 것은 표기뿐:
 * 한국어로 쓸 수 있는 영어와 꾸밈용 영어를 덜어냈다.
 */

export const metadata: Metadata = {
  title: '이용약관 — bar-menu',
  description: 'bar-menu QR 메뉴판 서비스의 이용약관과 요금·환불·해지 정책입니다.',
  alternates: { canonical: '/terms' },
};

/** 용어와 설명이 짝을 이루는 조항. 용어를 좁은 칸에 밀어 넣으면 낱말마다
    줄이 바뀌므로(예전 화면이 그랬다) 위아래로 쌓는다. */
type Def = { t: string; d: string };

const PLANS: Def[] = [
  {
    t: 'Entry · 월 9,900원',
    d: '기본 모바일 QR 메뉴판, 실시간 메뉴 편집, 이미지 자동 경량화, 주류 페어링 추천을 제공합니다.',
  },
  {
    t: 'Pro · 월 19,900원',
    d: 'Entry의 모든 기능에 더해 주문·결제 연동, 와이파이 간편 접속, 매장 외부 접근 제한(공인 IP·와이파이 SSID 기준), 복사·우클릭·인쇄 차단을 제공합니다.',
  },
  {
    t: 'Premium · 월 39,900원 (초기 디자인비 20만원 별도)',
    d: 'Pro의 모든 기능에 더해 매장 맞춤 카드 레이아웃 설계, 인트로 영상 제작 및 삽입, 다지점 계정 통합 관리, 연중무휴 우선 기술 지원을 제공합니다.',
  },
];

const PAYMENT: string[] = [
  '모든 구독 요금은 매월 지정된 정기 결제일에 선불로 자동 청구·결제됩니다.',
  '회원이 등록한 결제수단의 잔액 부족 등으로 결제에 실패하면 최대 3회까지 자동 재결제를 시도하며, 이후에도 미납이 계속되면 서비스가 자동으로 일시 정지될 수 있습니다.',
  '연체가 3개월 이상 계속되는 경우 누적 데이터의 보존 의무가 사라지며, 매장의 메뉴판 데이터와 설정값은 영구 삭제될 수 있습니다.',
];

const CANCEL: Def[] = [
  {
    t: '자유로운 해지',
    d: '본 서비스는 무약정 상품으로, 회원이 원할 때 언제든 해지를 신청할 수 있으며 해지 위약금은 발생하지 않습니다.',
  },
  {
    t: '구독 중도 해지',
    d: '구독 기간 도중에 해지를 신청하면 다음 결제 주기 전까지는 정상적으로 이용할 수 있고, 다음 결제일에 서비스가 종료됩니다.',
  },
  {
    t: '환불 조건',
    d: '결제 후 메뉴판에 메뉴를 등록하거나 QR 코드를 만드는 등 서비스를 실제로 개시하기 전이라면, 결제일로부터 7일 이내에 환불을 신청하실 때 전액 환불됩니다. 다만 Premium의 초기 디자인 제작 비용은 맞춤 디자인 작업이 시작된 뒤에는 환불되지 않습니다.',
  },
];

const WITHDRAW: Def[] = [
  {
    t: '제공 개시',
    d: '본 서비스는 배송이 없는 온라인 디지털 서비스입니다. 결제가 확인되는 즉시 손님용 메뉴판이 열리며, 그 시점부터 서비스가 개시된 것으로 봅니다.',
  },
  {
    t: '제공 기간',
    d: '1개월 단위로 제공되며, 해지하지 않으면 매월 같은 날 자동으로 갱신됩니다.',
  },
  {
    t: '청약철회',
    d: '결제일로부터 7일 이내이고 아직 서비스를 개시하지 않은 경우(메뉴 등록·QR 생성 등 이용 이력이 없는 경우) 청약철회하실 수 있으며 전액 환불됩니다.',
  },
  {
    t: '청약철회의 제한',
    d: '이미 서비스를 개시한 경우, 그리고 Premium의 맞춤 디자인 작업이 착수된 경우에는 그 부분에 한해 청약철회가 제한됩니다. 이 경우에도 남은 기간에 대한 해지는 언제든 가능합니다.',
  },
];

function Defs({ items }: { items: Def[] }) {
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

export default function TermsPage() {
  return (
    <>
      <Nav />

      <header className="wrap mkt-subhero">
        <div className="ko-lbl rule-lbl">이용약관</div>
        <h1 className="kd">
          서비스 이용약관 및
          <br />
          요금 정책
        </h1>
        {/* 공시일과 시행일이 같은 날이다. 두 번 적으면 좁은 화면에서 '16일'만
            다음 줄로 떨어진다. 한 줄로 합친다. */}
        <p className="bd">2026년 8월 16일 공시 · 같은 날 시행</p>
      </header>

      <div className="wrap mkt-legal">
        <section>
          <h2 className="kd">제1조 (목적 및 서비스 정의)</h2>
          <p className="sm">
            본 약관은 QR 메뉴판 서비스 &apos;bar-menu&apos;(이하 &apos;회사&apos;)가 제공하는 모바일
            메뉴판 제작·관리 및 결제 연동 구독 서비스의 이용과 관련하여, 회사와 가맹점주(이하
            &apos;회원&apos;) 사이의 권리·의무 및 책임 사항을 정하는 것을 목적으로 합니다.
          </p>
        </section>

        <section>
          <h2 className="kd">제2조 (무약정 구독 요금제)</h2>
          <p className="sm">
            &apos;bar-menu&apos;는 의무 사용 약정과 해지 위약금이 없는 정기 정액 구독 방식으로
            운영됩니다. 요금제는 아래 세 가지입니다. 표시 금액은 모두 부가세를 포함합니다.
          </p>
          <Defs items={PLANS} />
        </section>

        <section>
          <h2 className="kd">제3조 (요금 결제 및 연체)</h2>
          <Bullets items={PAYMENT} />
        </section>

        <section>
          <h2 className="kd">제4조 (해지 및 환불)</h2>
          <Defs items={CANCEL} />
        </section>

        <section>
          <h2 className="kd">제5조 (서비스 제공기간 및 청약철회)</h2>
          <Defs items={WITHDRAW} />
        </section>

        <section>
          <h2 className="kd">제6조 (결제 이의신청 및 분쟁 처리)</h2>
          <p className="sm">
            결제 금액·결제일·자동 갱신 등 결제 내역에 이의가 있으신 경우, 이 사이트 아래쪽에 안내된
            연락처나 문의하기를 통해 접수해 주시면 3영업일 이내에 확인 결과를 회신드립니다. 확인 결과
            회사의 착오로 인한 과오금이 있으면 전액을 즉시 환급하며, 결제수단으로 환급할 수 없을 때에는
            회원이 지정한 계좌로 지급합니다.
          </p>
          <p className="sm">
            회사와 회원 사이에 분쟁이 생긴 경우 양 당사자는 성실히 협의하며, 협의가 이루어지지 않을
            때에는 「전자상거래 등에서의 소비자보호에 관한 법률」에 따라 한국소비자원 등 관련 기관에
            조정을 신청할 수 있습니다.
          </p>
        </section>

        <section>
          <h2 className="kd">제7조 (보안 및 접근 제어 책임)</h2>
          <p className="sm">
            Pro 이상에서 제공되는 매장 IP·와이파이 SSID 제한과 복사·우클릭·인쇄 차단 기능은, 매장이
            쌓아 온 메뉴 구성이 밖으로 새지 않도록 돕는 보조 수단입니다. 매장의 공유기를 바꾸는 등으로
            공인 IP나 와이파이 SSID가 달라졌을 때에는 회원이 관리자 화면에서 즉시 정보를 갱신해야
            정상적으로 접근 제어가 동작합니다.
          </p>
          <p className="sm">
            손님 휴대폰의 운영체제가 제공하는 화면 캡처까지는 막지 못합니다.
          </p>
        </section>

        <section>
          <h2 className="kd">제8조 (면책)</h2>
          <p className="sm">
            회사는 클라우드 인프라 제공사 및 결제대행사의 자체 네트워크 장애로 생기는 일시적인 메뉴판
            노출 지연이나 결제 실패에 대하여는 책임을 지지 않습니다. 다만 회사의 귀책사유로 연속 24시간
            이상 전체 서비스 장애가 발생한 경우, 가맹점주의 요청에 따라 해당 월 요금의 일할 상당액을
            감면하거나 보상합니다.
          </p>
          <p className="note sm">
            라이선스 안내 — 이 서비스에 올리거나 제공받은 폰트 파일과 영상은 해당 가맹점주의 메뉴판
            안에서만 사용할 수 있습니다.
          </p>
        </section>
      </div>

      <Footer />
    </>
  );
}
