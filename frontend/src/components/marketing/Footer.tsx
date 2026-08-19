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
        </div>
      </div>
    </footer>
  );
}
