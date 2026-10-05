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

// 제목용 명조. 한글 글리프가 필요해서 subsets 를 지정하지 않고
// 구글이 주는 unicode-range 전부를 셀프호스팅한다.
//
// 700 은 제목(h1·h2), 800 은 히어로의 강조 낱말과 업종 마퀴가 쓴다.
// 제목이 첫 화면에 보이므로 preload 를 켠다 — 끄면 프리텐다드로 한 번
// 그려졌다가 명조로 바뀌면서 제목이 눈에 띄게 흔들린다.
const myeongjo = Nanum_Myeongjo({
  weight: ['700', '800'],
  variable: '--font-myeongjo',
  display: 'swap',
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
