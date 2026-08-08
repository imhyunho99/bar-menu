import { IBM_Plex_Mono, Nanum_Myeongjo } from 'next/font/google';
import RevealObserver from '@/components/marketing/RevealObserver';
import '@/styles/marketing.css';

// 라틴·숫자 라벨 전용. 한글에는 쓰지 않는다 (글리프가 없어 흩어져 보인다)
const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
  display: 'swap',
});

// 강조용 명조. 한글 글리프가 필요해서 subsets 를 지정하지 않고
// 구글이 주는 unicode-range 전부를 셀프호스팅한다 (preload 는 끈다).
const myeongjo = Nanum_Myeongjo({
  weight: '800',
  variable: '--font-myeongjo',
  display: 'swap',
  preload: false,
});

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  // 프리텐다드는 marketing.css 가 @import 로 물고 온다 (유니코드 레인지 92조각)
  return (
    <div className={`mkt ${mono.variable} ${myeongjo.variable}`}>
      {children}
      <RevealObserver />
    </div>
  );
}
