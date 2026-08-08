import Image from 'next/image';
import Link from 'next/link';

const LINKS = [
  { href: '/features', label: '기능' },
  { href: '/pricing', label: '요금' },
] as const;

/** 문의는 랜딩의 #contact 한 곳에만 있다. 하위 페이지에서는 앵커까지 붙여 넘긴다. */
export default function Nav({ active }: { active?: 'features' | 'pricing' }) {
  const contactHref = active ? '/#contact' : '#contact';

  return (
    <nav className="mkt-nav">
      <div className="wrap inner">
        <Link href="/" className="brand">
          <Image src="/marketing/logo-t.png" alt="" width={28} height={28} priority />
          <span className="kd">bar-menu</span>
          <span className="en-xs">QR Menu for Bars</span>
        </Link>
        <div className="links">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="nav-link"
              aria-current={active && l.href === `/${active}` ? 'page' : undefined}
            >
              {l.label}
            </Link>
          ))}
          <a href={contactHref} className="btn btn-solid">
            도입 문의
          </a>
        </div>
      </div>
    </nav>
  );
}
