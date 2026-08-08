import Image from 'next/image';
import Link from 'next/link';
import { signupUrl } from '@/lib/site';

const LINKS = [
  { href: '/features', label: '기능' },
  { href: '/pricing', label: '요금' },
  { href: '/guide', label: '도입 절차' },
] as const;

/**
 * 첫 번째 행동은 가입이고, 문의는 그 옆에 남겨둔다.
 *
 * 문의 폼은 여전히 랜딩의 #contact 한 곳에만 있다. 하위 페이지에서는 앵커까지 붙여 넘긴다.
 */
export default function Nav({ active }: { active?: 'features' | 'pricing' | 'guide' }) {
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
          <a href={contactHref} className="nav-link">
            문의
          </a>
          <a href={signupUrl} className="btn btn-solid">
            무료로 시작
          </a>
        </div>
      </div>
    </nav>
  );
}
