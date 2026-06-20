'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

interface NavigationRemoteProps {
  slug: string;
  prevCategory: { id: number; name: string } | null;
  nextCategory: { id: number; name: string } | null;
}

export default function NavigationRemote({ slug, prevCategory, nextCategory }: NavigationRemoteProps) {
  const router = useRouter();
  const [show, setShow] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      // 스크롤이 조금이라도 내려가면 리모컨을 표시
      if (window.scrollY > 50) {
        setShow(true);
      } else {
        setShow(false);
      }
    };

    window.addEventListener('scroll', handleScroll);
    handleScroll(); // 초기 상태 확인
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    });
  };

  return (
    <div className={`navigation-remote ${show ? 'show' : ''}`} id="navigationRemote">
      {prevCategory ? (
        <button
          className="remote-btn remote-btn-prev"
          onClick={() => router.push(`/${slug}/category/${prevCategory.id}`)}
          title={prevCategory.name}
        >
          <Image src="/left.png" alt="Prev Category" width={60} height={60} />
        </button>
      ) : (
        <div className="remote-btn remote-btn-prev" style={{ opacity: 0, pointerEvents: 'none' }}>
          <Image src="/left.png" alt="Prev Category" width={60} height={60} />
        </div>
      )}

      <button className="remote-btn remote-btn-top" onClick={scrollToTop} id="remoteTop">
        <Image src="/up.png" alt="Scroll Top" width={60} height={60} />
      </button>

      {nextCategory ? (
        <button
          className="remote-btn remote-btn-next"
          onClick={() => router.push(`/${slug}/category/${nextCategory.id}`)}
          title={nextCategory.name}
        >
          <Image src="/right.png" alt="Next Category" width={60} height={60} />
        </button>
      ) : (
        <div className="remote-btn remote-btn-next" style={{ opacity: 0, pointerEvents: 'none' }}>
          <Image src="/right.png" alt="Next Category" width={60} height={60} />
        </div>
      )}
    </div>
  );
}
