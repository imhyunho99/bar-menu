import Image from 'next/image';
import Link from 'next/link';

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
          <span>
            상호명 <span className="t-ink">bar-menu</span>
          </span>
          <span>
            대표 <span className="t-ink">나현호</span>
          </span>
          <span>
            사업자등록번호 <span className="t-ink num">102-13-82292</span>
          </span>
          <Link href="/terms" className="t-ink">
            이용약관
          </Link>
        </div>
      </div>
    </footer>
  );
}
