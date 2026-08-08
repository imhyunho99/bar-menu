'use client';

import Image from 'next/image';
import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { submitContact } from '@/lib/api';

const PLAN_LABEL: Record<string, string> = {
  entry: 'Entry',
  pro: 'Pro',
  premium: 'Premium',
};

function ContactForm() {
  // 요금 페이지의 "Pro 문의하기"는 /?plan=pro#contact 로 넘어온다
  const planParam = useSearchParams().get('plan') ?? '';
  const plan = planParam in PLAN_LABEL ? planParam : 'general';

  const [name, setName] = useState('');
  const [contactInfo, setContactInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !contactInfo.trim() || submitting) return;

    setSubmitting(true);
    setStatus(null);
    try {
      const res = await submitContact({ name, contact_info: contactInfo, plan });
      if (res.status === 'success') {
        setStatus({ ok: true, message: res.message });
        setName('');
        setContactInfo('');
      } else {
        setStatus({ ok: false, message: res.message || '접수에 실패했습니다. 잠시 후 다시 시도해 주세요.' });
      }
    } catch {
      setStatus({ ok: false, message: '네트워크 연결 상태를 확인해 주세요.' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="mkt-form" onSubmit={handleSubmit}>
      {plan !== 'general' && (
        <p className="ko-lbl chosen">관심 요금제 · {PLAN_LABEL[plan]}</p>
      )}
      <label>
        <span className="ko-lbl">매장명</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="달빛 이자카야"
          required
          autoComplete="organization"
        />
      </label>
      <label>
        <span className="ko-lbl">연락처 또는 이메일</span>
        <input
          value={contactInfo}
          onChange={(e) => setContactInfo(e.target.value)}
          placeholder="010-0000-0000"
          required
          autoComplete="tel"
        />
      </label>
      <button type="submit" disabled={submitting}>
        {submitting ? '보내는 중…' : '문의 보내기'}
      </button>
      <p className="cap note" role="status">
        {status ? status.message : '남겨주신 정보는 문의 응대에만 씁니다.'}
      </p>
    </form>
  );
}

export default function ContactSection() {
  return (
    <section id="contact" className="mkt-contact grain">
      <Image
        src="/marketing/contact-dining.jpg"
        alt=""
        width={2000}
        height={1333}
        sizes="100vw"
        className="bgshot"
      />
      <div className="veil" />
      <div className="over">
        <div className="wrap cols">
          <div className="lead">
            <div className="ko-lbl rule-lbl">도입 문의</div>
            <h2 className="kd">
              매장명과 연락처만
              <br />
              남겨주세요
            </h2>
            <p className="bd">
              받는 즉시 확인하고 안내드리겠습니다. 상담이 부담스러우시면 문자로만 진행해도 됩니다.
            </p>
          </div>
          <Suspense fallback={null}>
            <ContactForm />
          </Suspense>
        </div>
      </div>
    </section>
  );
}
