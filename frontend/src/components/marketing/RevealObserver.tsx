'use client';

import { useEffect } from 'react';

/**
 * .reveal 요소를 화면에 들어올 때 한 번씩 켠다.
 * 요소마다 컴포넌트를 감싸는 대신 관찰자 하나가 페이지 전체를 훑는다.
 */
export default function RevealObserver() {
  useEffect(() => {
    const targets = document.querySelectorAll<HTMLElement>('.mkt .reveal');
    if (!targets.length) return;

    // 모션을 끈 사용자에게는 관찰 없이 즉시 보여준다
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      targets.forEach((el) => el.classList.add('in'));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (!e.isIntersecting) return;
          e.target.classList.add('in');
          io.unobserve(e.target);
        });
      },
      { rootMargin: '0px 0px -6% 0px', threshold: 0.05 }
    );

    targets.forEach((el, i) => {
      // 같은 행에 있는 카드들이 한 박자씩 어긋나게 들어온다
      el.style.transitionDelay = `${(i % 3) * 70}ms`;
      io.observe(el);
    });

    return () => io.disconnect();
  }, []);

  return null;
}
