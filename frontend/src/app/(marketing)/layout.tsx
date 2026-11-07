import RevealObserver from '@/components/marketing/RevealObserver';
import { mono, myeongjo } from '@/lib/marketing-fonts';
import '@/styles/marketing.css';

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  // 프리텐다드는 marketing.css 가 @import 로 물고 온다 (유니코드 레인지 92조각)
  return (
    <div className={`mkt ${mono.variable} ${myeongjo.variable}`}>
      {children}
      <RevealObserver />
    </div>
  );
}
