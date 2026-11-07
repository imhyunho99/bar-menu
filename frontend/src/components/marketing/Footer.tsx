import Image from 'next/image';
import Link from 'next/link';
import { BUSINESS_SHOWN } from '@/lib/business';

export default function Footer() {
  return (
    <footer className="mkt-footer">
      <div className="wrap inner">
        <Link href="/" className="brand">
          <Image src="/marketing/logo-t.png" alt="" width={24} height={24} />
          <span className="kd" style={{ fontSize: 15 }}>
            bar-menu
          </span>
        </Link>
        <div className="cap biz">
          {BUSINESS_SHOWN.map((field) => (
            <span key={field.label}>
              {field.label} <span className="t-ink">{field.value}</span>
            </span>
          ))}
          <Link href="/terms" className="t-ink">
            이용약관
          </Link>
          {/* 처리방침은 굵게 둔다 — 개인정보 보호위원회 작성지침이 다른 약관과
              구분되게 표시하라고 한다. */}
          <Link href="/privacy" className="t-ink" style={{ fontWeight: 700 }}>
            개인정보 처리방침
          </Link>
        </div>
      </div>
    </footer>
  );
}
