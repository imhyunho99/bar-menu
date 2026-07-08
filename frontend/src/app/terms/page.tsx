import Link from 'next/link';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '서비스 이용약관 및 요금정책 | bar-menu',
  description: 'bar-menu 스마트 QR 메뉴판 서비스의 이용약관, 요금 결제, 환불 및 해지 정책 안내입니다.',
};

export default function TermsPage() {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: `
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Noto+Sans+KR:wght@300;400;700;900&display=swap');

        :root {
            --bg-color: #080710;
            --card-bg: rgba(255, 255, 255, 0.03);
            --card-border: rgba(255, 255, 255, 0.08);
            --primary: #8a2be2;
            --primary-glow: rgba(138, 43, 226, 0.2);
            --secondary: #00f2fe;
            --text-primary: #ffffff;
            --text-secondary: #a0a0c0;
            --gradient: linear-gradient(135deg, #8a2be2 0%, #4a00e0 50%, #00f2fe 100%);
            --font-en: 'Outfit', sans-serif;
            --font-ko: 'Noto Sans KR', sans-serif;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: var(--font-ko);
            overflow-x: hidden;
            line-height: 1.7;
            word-break: keep-all;
            overflow-wrap: break-word;
            margin: 0;
        }

        .wrapper {
            max-width: 800px;
            margin: 0 auto;
            padding: 60px 24px 100px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 30px;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: 50px;
        }

        .header-logo {
            font-family: var(--font-en);
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: 2px;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
            text-decoration: none;
        }

        .back-btn {
            font-size: 0.9rem;
            color: var(--secondary);
            text-decoration: none;
            font-weight: 700;
            transition: all 0.2s ease;
        }

        .back-btn:hover {
            text-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
        }

        h1 {
            font-size: 2.2rem;
            font-weight: 900;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #ffffff 0%, #a0a0c0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .last-update {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 40px;
        }

        .policy-container {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 40px 30px;
            backdrop-filter: blur(10px);
        }

        .policy-section {
            margin-bottom: 35px;
        }

        .policy-section:last-child {
            margin-bottom: 0;
        }

        h2 {
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--secondary);
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        h2::before {
            content: '';
            display: inline-block;
            width: 4px;
            height: 18px;
            background: var(--gradient);
            border-radius: 2px;
        }

        p {
            color: var(--text-secondary);
            font-size: 0.95rem;
            margin-bottom: 15px;
            text-align: justify;
        }

        ul {
            list-style: none;
            padding: 0;
            margin: 0 0 15px 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        li {
            font-size: 0.95rem;
            color: var(--text-secondary);
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }

        li::before {
            content: '•';
            color: var(--primary);
            font-weight: 800;
        }

        .highlight-box {
            background: rgba(138, 43, 226, 0.05);
            border: 1px dashed rgba(138, 43, 226, 0.3);
            border-radius: 10px;
            padding: 20px;
            margin-top: 15px;
        }

        .highlight-box p {
            margin: 0;
            font-size: 0.9rem;
            color: #d8b4fe;
        }

        footer {
            margin-top: 50px;
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
            border-top: 1px solid var(--card-border);
            padding-top: 30px;
        }
      ` }} />

      <div className="wrapper">
        <header>
          <Link href="/" className="header-logo">bar-menu</Link>
          <Link href="/" className="back-btn">← 홈으로 가기</Link>
        </header>

        <main>
          <h1>서비스 이용약관 및 요금정책</h1>
          <div className="last-update">공시일자: 2026년 7월 8일 (시행일자: 2026년 7월 8일)</div>

          <div className="policy-container">
            <section className="policy-section">
              <h2>제 1 조 (목적 및 서비스 정의)</h2>
              <p>
                본 약관은 스마트 QR 메뉴판 솔루션 &apos;bar-menu&apos;(이하 &apos;회사&apos;)가 제공하는 모바일 메뉴판 제작, 관리 및 결제 연동 SaaS 서비스의 이용과 관련하여 회사와 가맹점주(이하 &apos;회원&apos;) 간의 권리, 의무 및 책임 사항을 규정함을 목적으로 합니다.
              </p>
            </section>

            <section className="policy-section">
              <h2>제 2 조 (무약정 구독 요금제 정의)</h2>
              <p>
                &apos;bar-menu&apos;는 별도의 의무 사용 약정 및 해지 위약금이 없는 정기 정액 구독 방식으로 운영됩니다. 요금제는 아래의 세 가지 플랜으로 나뉩니다.
              </p>
              <ul>
                <li><strong>Entry Plan (월 9,900원)</strong>: 기본 모바일 QR 메뉴판, 실시간 메뉴 편집 엔진, WebP 이미지 변환, 주류 페어링 연동 제공.</li>
                <li><strong>Pro Plan (월 19,900원)</strong>: Entry의 모든 기능 + 페이히어 결제/장바구니 API 연동, 와이파이 간편 접속 제공, 매장 외부 접근 제한(IP/SSID 매칭) 보안, 스크린샷 캡처 차단 제공.</li>
                <li><strong>Premium Plan (월 39,900원, 초기 디자인비 20만원 별도)</strong>: Pro의 모든 기능 + 매장 커스텀 카드 레이아웃 빌더 세팅, 인트로/로딩용 프리미엄 비디오 제작 및 삽입, 다지점 프랜차이즈 계정 통합 관리, 24/7 우선 기술 지원.</li>
              </ul>
            </section>

            <section className="policy-section">
              <h2>제 3 조 (요금 결제 및 연체 정책)</h2>
              <ul>
                <li>모든 구독 요금은 매월 지정된 정기 결제일에 선불로 자동 청구 및 결제됩니다.</li>
                <li>회원이 등록한 결제수단의 잔액부족 등의 사유로 결제 실패 시, 최대 3회의 자동 재결제를 시도하며, 이후에도 미납 상태가 지속될 경우 서비스가 자동 일시 정지될 수 있습니다.</li>
                <li>연체 상태가 3개월 이상 지속되는 경우, 누적 데이터의 보존 의무가 소멸되며 매장의 메뉴판 데이터 및 세팅 값은 영구 삭제 처리될 수 있습니다.</li>
              </ul>
            </section>

            <section className="policy-section">
              <h2>제 4 조 (해지 및 환불 정책)</h2>
              <ul>
                <li><strong>자유로운 해지</strong>: 본 서비스는 무약정 상품으로 회원이 원할 때 언제든 해지 신청이 가능하며, 해지 위약금은 절대 발생하지 않습니다.</li>
                <li><strong>구독 중도 해약 시</strong>: 구독 기간 도중에 사용자가 해지를 신청하는 경우 다음 결제 주기 전까지는 정상 이용이 가능하며, 다음 결제일에 서비스가 종료됩니다.</li>
                <li><strong>환불 조건</strong>: 결제 후 메뉴판에 메뉴 데이터를 등록하거나 QR 코드를 생성하는 등 서비스를 실제 개시하기 이전에 한해 결제일로부터 7일 이내 환불 신청 시 100% 전액 환불됩니다. 다만, Premium Plan의 초기 디자인 제작 비용은 맞춤 디자인 용역이 시작된 이후에는 환불이 불가합니다.</li>
              </ul>
            </section>

            <section className="policy-section">
              <h2>제 5 조 (보안 및 접근 제어 책임)</h2>
              <p>
                Pro Plan 이상에서 제공되는 매장 IP/SSID 제한 및 스크린샷 금지 기능은 외부로부터 매장 독자적인 지적 재산과 메뉴 노출을 보호하기 위한 보조적 수단입니다. 회원은 매장의 공유기 변경 등으로 공인 IP나 와이파이 SSID가 변경되었을 경우 즉시 관리자 페이지에서 정보를 갱신해야 정상적인 접속 제어 혜택을 누릴 수 있습니다.
              </p>
            </section>

            <section className="policy-section">
              <h2>제 6 조 (서비스 면책 조항)</h2>
              <p>
                회사는 클라우드 인프라 파트너(Vercel, Next.js 등) 및 PG 사(페이히어 등)의 자체 네트워크 장애로 인하여 발생하는 일시적인 메뉴판 노출 지연 혹은 결제 실패에 대하여는 책임을 지지 않습니다. 단, 회사의 귀책 사유로 인하여 연속 24시간 이상 전체 서비스 장애가 발생하는 경우 가맹점주의 요청에 의해 해당 월 요금의 일할 상당액을 감면 또는 보상합니다.
              </p>
              <div className="highlight-box">
                <p>
                  ※ bar-menu의 라이선스 안내: 본 플랫폼 내에서 커스텀 매니저로 업로드하거나 제공되는 폰트 파일 및 비디오 에셋은 해당 가맹점주의 메뉴판 템플릿 영역 내에서만 안전하게 사용 가능하도록 허용됩니다.
                </p>
              </div>
            </section>
          </div>
        </main>

        <footer>
          <p>&copy; 2026 bar-menu. All Rights Reserved. 스마트한 바(Bar) 비즈니스의 시작.</p>
        </footer>
      </div>
    </>
  );
}
