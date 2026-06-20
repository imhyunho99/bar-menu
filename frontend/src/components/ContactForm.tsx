'use client';

import { useState } from 'react';
import { submitContact } from '@/lib/api';

export default function ContactForm() {
  const [name, setName] = useState('');
  const [contactInfo, setContactInfo] = useState('');
  const [plan, setPlan] = useState('general');
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // 외부(예: 요금제 버튼 클릭)에서 Plan을 선택할 수 있도록 이벤트를 리스닝할 수 있음
  // window 객체에 selectPlan 함수를 전역 등록하여 HTML onclick과 연동되게 처리
  if (typeof window !== 'undefined') {
    (window as any).selectPlan = (planId: string) => {
      setPlan(planId);
      // 문의하기 섹션으로 스크롤
      document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' });
    };
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !contactInfo) return;

    setSubmitting(true);
    setStatus(null);

    try {
      const res = await submitContact({ name, contact_info: contactInfo, plan });
      if (res.status === 'success') {
        setStatus({ type: 'success', message: res.message });
        setName('');
        setContactInfo('');
        setPlan('general');
      } else {
        setStatus({ type: 'error', message: res.message || '오류가 발생했습니다.' });
      }
    } catch {
      setStatus({ type: 'error', message: '네트워크 연결 상태를 확인해 주세요.' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="contact-form">
      <div className="form-group">
        <label htmlFor="id_name" className="form-label">이름 또는 업체명 (매장명)</label>
        <input
          type="text"
          id="id_name"
          className="form-input"
          placeholder="이름 또는 매장명을 입력해 주세요"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="id_contact" className="form-label">연락처 또는 이메일</label>
        <input
          type="text"
          id="id_contact"
          className="form-input"
          placeholder="연락처 또는 이메일을 입력해 주세요"
          value={contactInfo}
          onChange={(e) => setContactInfo(e.target.value)}
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="id_plan" className="form-label">관심 요금제</label>
        <select
          id="id_plan"
          className="form-input"
          style={{ backgroundColor: '#080710', color: 'white' }}
          value={plan}
          onChange={(e) => setPlan(e.target.value)}
        >
          <option value="general">일반 문의 (선택 안 함)</option>
          <option value="standard">Standard 요금제</option>
          <option value="pro">Pro 요금제</option>
          <option value="premium">Premium 요금제</option>
        </select>
      </div>
      <button type="submit" className="submit-btn" disabled={submitting}>
        {submitting ? '접수 중...' : '문의 접수하기'}
      </button>
      {status && (
        <div className={`form-status ${status.type}`}>
          {status.message}
        </div>
      )}
    </form>
  );
}
