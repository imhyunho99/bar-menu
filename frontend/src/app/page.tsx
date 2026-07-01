import { getRestaurants } from '@/lib/api';
import Link from 'next/link';
import Image from 'next/image';
import ContactForm from '@/components/ContactForm';
import type { Restaurant } from '@/lib/types';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'bar-menu | 관리자 맞춤형 스마트 QR 메뉴판 서비스',
  description: '강남, 홍대, 성수 등 전국의 트렌디한 한식 펍, 바, 다이닝 매장을 위한 실시간 디자인 커스텀 QR 메뉴판 솔루션 bar-menu. 폰트/컬러 최적화, 초경량 WebP 변환, 주류 페어링 연동으로 매출을 올리세요.',
  keywords: 'QR메뉴판, 스마트메뉴판, 모바일메뉴판, 테이블오더, 강남 QR메뉴판, 홍대 QR메뉴판, 성수 QR메뉴판, 바메뉴판, 펍메뉴판, 주류페어링, bar-menu',
  openGraph: {
    type: 'website',
    url: 'https://bar-menu.ddnsfree.com/',
    title: 'bar-menu | 관리자 맞춤형 스마트 QR 메뉴판 서비스',
    description: '실시간 관리 및 디자인 커스터마이징이 가능한 스마트 QR 메뉴판 솔루션. 초경량 WebP 기술 탑재.',
    images: [{ url: '/site_images/logo.png' }],
  },
};

export default async function LandingPage() {
  let restaurants: Restaurant[] = [];

  try {
    restaurants = await getRestaurants();
  } catch (err) {
    console.error('Failed to load restaurants on landing page:', err);
  }

  // Google SEO Schema.json
  const schemaJson = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    'name': 'bar-menu',
    'operatingSystem': 'All',
    'applicationCategory': 'BusinessApplication',
    'aggregateRating': {
      '@type': 'AggregateRating',
      'ratingValue': '4.9',
      'ratingCount': '124',
    },
    'offers': {
      '@type': 'Offer',
      'price': '0',
      'priceCurrency': 'KRW',
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaJson) }}
      />
      <style dangerouslySetInnerHTML={{ __html: `
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Noto+Sans+KR:wght@300;400;700;900&display=swap');

        :root {
            --bg-color: #080710;
            --card-bg: rgba(255, 255, 255, 0.03);
            --card-border: rgba(255, 255, 255, 0.08);
            --primary: #8a2be2;
            --primary-glow: rgba(138, 43, 226, 0.4);
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
            line-height: 1.6;
            word-break: keep-all;
            overflow-wrap: break-word;
        }

        .glow-orb {
            position: absolute;
            width: 600px;
            height: 600px;
            border-radius: 50%;
            background: radial-gradient(circle, var(--primary-glow) 0%, rgba(8, 7, 16, 0) 70%);
            z-index: -1;
            filter: blur(80px);
            pointer-events: none;
        }

        .orb-top-right {
            top: -200px;
            right: -200px;
        }

        .orb-bottom-left {
            bottom: -300px;
            left: -200px;
        }

        .wrapper {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 30px 0;
            border-bottom: 1px solid var(--card-border);
        }

        .header-logo {
            font-family: var(--font-en);
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: 2px;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .nav-btn {
            font-family: var(--font-ko);
            font-weight: 700;
            font-size: 0.9rem;
            text-decoration: none;
            color: var(--text-primary);
            padding: 10px 24px;
            border-radius: 30px;
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            transition: all 0.3s ease;
        }

        .nav-btn:hover {
            border-color: var(--secondary);
            box-shadow: 0 0 15px rgba(0, 242, 254, 0.3);
            transform: translateY(-2px);
        }

        .nav-btn-primary {
            background: var(--gradient);
            border: none;
            color: white !important;
        }

        .nav-btn-primary:hover {
            box-shadow: 0 0 25px var(--primary-glow);
        }

        .hero {
            padding: 100px 0 60px;
            text-align: center;
            position: relative;
        }

        .hero-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            background: rgba(138, 43, 226, 0.1);
            border: 1px solid rgba(138, 43, 226, 0.3);
            color: var(--secondary);
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 24px;
            letter-spacing: 1px;
            font-family: var(--font-en);
        }

        h1 {
            font-size: 3rem;
            font-weight: 900;
            letter-spacing: -0.5px;
            line-height: 1.25;
            margin-bottom: 24px;
        }

        h1 span {
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-desc {
            font-size: 1.2rem;
            color: var(--text-secondary);
            max-width: 700px;
            margin: 0 auto 40px;
            font-weight: 300;
        }

        .hero-buttons {
            display: flex;
            justify-content: center;
            gap: 16px;
            margin-bottom: 60px;
        }

        .features {
            padding: 80px 0;
        }

        .section-title {
            text-align: center;
            font-size: 2rem;
            font-weight: 900;
            margin-bottom: 16px;
        }

        .section-subtitle {
            text-align: center;
            color: var(--text-secondary);
            max-width: 600px;
            margin: 0 auto 50px;
            font-weight: 300;
            font-size: 1rem;
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 24px;
        }

        .feature-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 35px 30px;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }

        .feature-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, transparent 60%, rgba(138, 43, 226, 0.05) 100%);
            pointer-events: none;
        }

        .feature-card:hover {
            transform: translateY(-8px);
            border-color: rgba(138, 43, 226, 0.4);
            box-shadow: 0 12px 30px rgba(138, 43, 226, 0.15);
        }

        .feature-icon {
            font-size: 2.2rem;
            margin-bottom: 20px;
        }

        .feature-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 12px;
            color: var(--text-primary);
        }

        .feature-desc {
            font-size: 0.95rem;
            color: var(--text-secondary);
            line-height: 1.6;
        }

        .geo-section {
            padding: 60px 0;
            border-top: 1px solid var(--card-border);
            border-bottom: 1px solid var(--card-border);
            background: rgba(255, 255, 255, 0.01);
            text-align: center;
        }

        .geo-grid {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 16px;
            margin-top: 30px;
        }

        .geo-tag {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--card-border);
            border-radius: 30px;
            padding: 10px 20px;
            font-size: 0.9rem;
            color: var(--text-secondary);
            transition: all 0.2s ease;
        }

        .geo-tag:hover {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .partners {
            padding: 80px 0;
            text-align: center;
        }

        .partner-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            max-width: 900px;
            margin: 40px auto 0;
        }

        .partner-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 24px;
            text-decoration: none;
            color: var(--text-primary);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
        }

        .partner-card:hover {
            background: linear-gradient(90deg, rgba(138, 43, 226, 0.15) 0%, rgba(0, 242, 254, 0.05) 100%);
            border-color: var(--secondary);
            transform: scale(1.03);
            box-shadow: 0 8px 20px rgba(0, 242, 254, 0.1);
        }

        .partner-name {
            font-size: 1.1rem;
            font-weight: 700;
        }

        .partner-link-text {
            font-size: 0.85rem;
            color: var(--secondary);
            font-weight: 700;
            font-family: var(--font-en);
            letter-spacing: 1px;
        }

        footer {
            padding: 40px 0;
            border-top: 1px solid var(--card-border);
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }

        .contact-section {
            padding: 80px 0;
            border-top: 1px solid var(--card-border);
            text-align: center;
        }

        .contact-container {
            max-width: 600px;
            margin: 40px auto 0;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 40px 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            text-align: left;
        }

        .contact-form {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .form-label {
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .form-input {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 14px 16px;
            color: white;
            font-size: 1rem;
            font-family: var(--font-ko);
            transition: all 0.3s ease;
        }

        .form-input:focus {
            outline: none;
            border-color: var(--secondary);
            box-shadow: 0 0 10px rgba(0, 242, 254, 0.2);
            background: rgba(255, 255, 255, 0.06);
        }

        .submit-btn {
            background: var(--gradient);
            border: none;
            border-radius: 8px;
            padding: 16px;
            color: white;
            font-size: 1.1rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }

        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px var(--primary-glow);
        }

        .submit-btn:active {
            transform: translateY(0);
        }

        .form-status {
            margin-top: 15px;
            font-size: 0.95rem;
            text-align: center;
            padding: 10px;
            border-radius: 8px;
        }

        .form-status.success {
            background: rgba(46, 213, 115, 0.1);
            color: #2ed573;
            border: 1px solid rgba(46, 213, 115, 0.2);
        }

        .form-status.error {
            background: rgba(255, 71, 87, 0.1);
            color: #ff4757;
            border: 1px solid rgba(255, 71, 87, 0.2);
        }

        .footer-info {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 15px;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .footer-info span {
            position: relative;
        }

        @media (min-width: 769px) {
            .footer-info span:not(:last-child)::after {
                content: '|';
                position: absolute;
                right: -12px;
                color: var(--card-border);
            }
        }

        .pricing-section {
            padding: 80px 0;
            border-top: 1px solid var(--card-border);
            text-align: center;
        }

        .pricing-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }

        .pricing-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 40px 30px;
            display: flex;
            flex-direction: column;
            align-items: center;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            position: relative;
            overflow: hidden;
        }

        .pricing-card.featured {
            border-color: var(--primary);
            box-shadow: 0 10px 30px rgba(138, 43, 226, 0.15);
            background: linear-gradient(180deg, rgba(138, 43, 226, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        }

        .pricing-card.featured::after {
            content: 'POPULAR';
            position: absolute;
            top: 15px;
            right: -35px;
            background: var(--gradient);
            color: white;
            font-size: 0.7rem;
            font-weight: 800;
            padding: 4px 30px;
            transform: rotate(45deg);
            letter-spacing: 1px;
        }

        .pricing-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 15px 35px rgba(138, 43, 226, 0.2);
            border-color: rgba(138, 43, 226, 0.5);
        }

        .plan-name {
            font-size: 1.5rem;
            font-weight: 800;
            margin-bottom: 15px;
            color: var(--text-primary);
        }

        .plan-price-box {
            margin-bottom: 30px;
            text-align: center;
        }

        .price-setup {
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--secondary);
            margin-bottom: 5px;
        }

        .price-maintenance {
            font-size: 0.9rem;
            color: var(--text-secondary);
            font-weight: 400;
            line-height: 1.5;
        }

        .plan-features-list {
            list-style: none;
            padding: 0;
            margin: 0 0 35px 0;
            width: 100%;
            text-align: left;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .plan-feature-item {
            font-size: 0.95rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .plan-feature-item::before {
            content: '✓';
            color: var(--secondary);
            font-weight: 800;
        }

        .plan-cta-btn {
            width: 100%;
            padding: 14px;
            border-radius: 8px;
            border: 1px solid var(--card-border);
            background: rgba(255, 255, 255, 0.03);
            color: white;
            font-weight: 700;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            text-decoration: none;
            margin-top: auto;
        }

        .pricing-card.featured .plan-cta-btn {
            background: var(--gradient);
            border: none;
        }

        .plan-cta-btn:hover {
            background: var(--gradient);
            border-color: transparent;
            box-shadow: 0 5px 15px var(--primary-glow);
            transform: translateY(-2px);
            color: white;
        }

        @media (max-width: 768px) {
            h1 {
                font-size: 2.2rem;
            }
            .hero {
                padding: 60px 0 40px;
            }
            .hero-desc {
                font-size: 1rem;
            }
            .hero-buttons {
                flex-direction: column;
                align-items: center;
            }
            .nav-links {
                gap: 10px;
            }
        }
      ` }} />

      <div className="glow-orb orb-top-right"></div>
      <div className="glow-orb orb-bottom-left"></div>

      <div className="wrapper">
        <header>
          <div className="logo-container" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Image src="/site_images/logo.png" alt="bar-menu logo" width={32} height={32} style={{ objectFit: 'contain' }} />
            <span className="header-logo">bar-menu</span>
          </div>
          <div className="nav-links">
            <Link href="#demo" className="nav-btn nav-btn-primary">체험 매장 보기</Link>
          </div>
        </header>

        <section className="hero">
          <div className="hero-badge">PREMIUM QR MENU SOLUTION</div>
          <h1>터치 한 번으로 바뀌는 매장의 분위기,<br /><span>디자인 커스텀 QR 메뉴판 bar-menu</span></h1>
          <p className="hero-desc">
            강남, 홍대, 성수 등 전국의 트렌디한 이자카야, 와인바, 전통 주점을 위한 최적의 비대면 오더 파트너.
            매장 분위기에 맞춰 폰트, 색상, 레이아웃을 마음대로 디자인하세요.
          </p>
          <div className="hero-buttons">
            <Link href="#contact" className="nav-btn nav-btn-primary">제휴 문의하기</Link>
            <Link href="#features" className="nav-btn">주요 기능 둘러보기</Link>
          </div>
        </section>

        <section className="features" id="features">
          <h2 className="section-title">스마트 어드민을 위한 최상의 기능</h2>
          <p className="section-subtitle">단순한 글자 나열식 메뉴판이 아닙니다. 매장의 가치를 극대화할 수 있는 강력한 기능이 준비되어 있습니다.</p>

          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🎨</div>
              <h3 className="feature-title">비주얼 디자인 매니저</h3>
              <p className="feature-desc">우리 브랜드 전용 폰트 파일 업로드부터 카드 색상, 불투명도, 배경 이미지 서빙까지 마우스 클릭 몇 번으로 완벽 구현.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">⚡</div>
              <h3 className="feature-title">초경량 WebP 이미지 엔진</h3>
              <p className="feature-desc">지하 매장이나 복잡한 핫플레이스에서도 0.3초 만에 메뉴판이 열립니다. 이미지를 올리면 초경량 WebP 포맷으로 자동 변환됩니다.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🥂</div>
              <h3 className="feature-title">스마트 주류 페어링 연동</h3>
              <p className="feature-desc">특정 메뉴와 찰떡궁합인 주류/음료를 모달 하단에 매력적인 카드로 보여주어, 추가 주문과 세트 매출 상승을 즉각 유도합니다.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📱</div>
              <h3 className="feature-title">완성도 높은 모바일 레이아웃</h3>
              <p className="feature-desc">테이블 모드, 콤보 카드 모드 등 매장의 대표 메뉴 구성 형태에 따라 고객 경험(UX)을 극대화한 UI 뷰 타입을 즉시 스위칭합니다.</p>
            </div>
          </div>
        </section>

        <section className="geo-section">
          <h2 className="section-title">트렌디한 상권에서 입증된 솔루션</h2>
          <p className="section-subtitle">지역별 힙한 골목길 매장들의 개성 있는 아이덴티티를 그대로 녹여내는 다이나믹 스마트 메뉴판.</p>
          <div className="geo-grid">
            <span className="geo-tag">#성수동 와인바</span>
            <span className="geo-tag">#강남역 이자카야</span>
            <span className="geo-tag">#홍대 힙한 요리주점</span>
            <span className="geo-tag">#을지로 감성 펍</span>
            <span className="geo-tag">#한남동 다이닝바</span>
            <span className="geo-tag">#부산 해운대 테라스 펍</span>
          </div>
        </section>

        <section className="pricing-section" id="pricing">
          <h2 className="section-title">합리적인 도입 요금제</h2>
          <p className="section-subtitle">매장 규모와 브랜딩 니즈에 맞춘 세 가지 옵션을 제공합니다.</p>

          <div className="pricing-grid">
            <div className="pricing-card">
              <h3 className="plan-name">Standard</h3>
              <div className="plan-price-box">
                <div className="price-setup">구축비 50만원</div>
                <div className="price-maintenance">유지비 월 3만원 또는 연 30만원 (택 1)</div>
              </div>
              <ul className="plan-features-list">
                <li className="plan-feature-item">초기 메뉴판 데이터 구축 (기존 지면/이미지 기준)</li>
                <li className="plan-feature-item">기본 테마 및 레이아웃 제공</li>
                <li className="plan-feature-item">초경량 WebP 최적화 기본 적용</li>
                <li className="plan-feature-item">주류 페어링 연동 기본 적용</li>
              </ul>
              <Link href="#contact" className="plan-cta-btn">Standard 도입 문의</Link>
            </div>

            <div className="pricing-card featured">
              <h3 className="plan-name">Pro</h3>
              <div className="plan-price-box">
                <div className="price-setup">구축비 80만원</div>
                <div className="price-maintenance">유지비 월 5만원 또는 연 50만원 (택 1)</div>
              </div>
              <ul className="plan-features-list">
                <li className="plan-feature-item"><strong>Standard의 모든 혜택 포함</strong></li>
                <li className="plan-feature-item">매장 맞춤형 프리미엄 디자인 고도화</li>
                <li className="plan-feature-item">인트로/로딩용 랜딩 비디오 제작 및 삽입</li>
                <li className="plan-feature-item">관리자 최적화 전용 서체 및 스타일 패키지</li>
              </ul>
              <Link href="#contact" className="plan-cta-btn">Pro 도입 문의</Link>
            </div>

            <div className="pricing-card">
              <h3 className="plan-name">Premium</h3>
              <div className="plan-price-box">
                <div className="price-setup">가격 상담 문의</div>
                <div className="price-maintenance">요구사항에 맞춰 견적 산정</div>
              </div>
              <ul className="plan-features-list">
                <li className="plan-feature-item">커스텀 추가 기능 및 비즈니스 로직 개발</li>
                <li className="plan-feature-item">프랜차이즈 다지점 통합 관리자 계정 구성</li>
                <li className="plan-feature-item">전문 디자이너 1:1 전담 브랜딩 컨설팅</li>
                <li className="plan-feature-item">24/7 우선 기술 지원 서비스</li>
              </ul>
              <Link href="#contact" className="plan-cta-btn">Premium 도입 문의</Link>
            </div>
          </div>
        </section>

        <section className="contact-section" id="contact">
          <h2 className="section-title">제휴 및 도입 문의</h2>
          <p className="section-subtitle">bar-menu와 함께 스마트한 매장 관리를 시작해 보세요. 빠른 시일 내에 안내해 드리겠습니다.</p>
          <div className="contact-container">
            <ContactForm />
          </div>
        </section>

        <section className="partners" id="demo">
          <h2 className="section-title">이용 중인 매장 체험</h2>
          <p className="section-subtitle">실제 bar-menu 디자인 시스템과 주류 페어링 연동이 구현된 매장 데모입니다.</p>
          <div className="partner-list">
            {restaurants.map((restaurant) => (
              <Link href={`/${restaurant.slug}`} key={restaurant.id} className="partner-card">
                <span className="partner-name">{restaurant.name}</span>
                <span className="partner-link-text">VIEW MENU →</span>
              </Link>
            ))}
            {restaurants.length === 0 && (
              <div style={{ gridColumn: '1/-1', color: 'var(--text-secondary)', padding: '40px' }}>
                등록된 매장이 없습니다.
              </div>
            )}
          </div>
        </section>

        <footer>
          <div className="footer-info">
            <span>상호명: bar-menu</span>
            <span>대표자 성명: 나현호</span>
            <span>사업자등록번호: 102-13-82292</span>
          </div>
          <p>&copy; 2026 bar-menu. All Rights Reserved. 디자인 및 실시간 편집에 특화된 스마트 QR 메뉴판 서비스.</p>
        </footer>
      </div>
    </>
  );
}
