'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRestaurant } from '../context';

/**
 * 주소A — QR 전용 진입점.
 * QR로 접속한 손님만 이 경로를 타며, 로딩 비디오를 재생한 뒤 메뉴(주소B)로 넘긴다.
 * 링크로 직접 들어온 손님은 이 경로를 거치지 않으므로 비디오를 보지 않는다.
 * layout.tsx의 IP 게이트가 이 경로에도 적용되므로, 와이파이 미연결 시에는
 * 이 컴포넌트가 렌더되기 전에 잠금화면(주소C)이 대신 반환된다.
 */
type Phase = 'intro' | 'manual' | 'done';

export default function EnterPage() {
  const { restaurant } = useRestaurant();
  const settings = restaurant.site_settings;
  const slug = restaurant.slug;
  const router = useRouter();

  const introVideo = settings?.intro_video || null;
  const manualVideo = settings?.loading_video_2 || null;

  const [phase, setPhase] = useState<Phase>(
    introVideo ? 'intro' : manualVideo ? 'manual' : 'done'
  );
  const videoRef = useRef<HTMLVideoElement>(null);

  const advance = () => {
    setPhase((p) => (p === 'intro' && manualVideo ? 'manual' : 'done'));
  };

  // 재생이 끝났거나 재생할 게 없으면 메뉴로 넘어간다.
  useEffect(() => {
    if (phase === 'done') {
      router.replace(`/${slug}`);
    }
  }, [phase, slug, router]);

  // 자동재생 시작 여부 감시: 6초 안에 재생이 시작되지 않으면(모바일 autoplay 차단 등)
  // 다음 단계로 넘긴다. 재생 중인 영상은 자르지 않는다(onEnded가 종료를 담당).
  useEffect(() => {
    if (phase === 'done') return;
    const video = videoRef.current;
    if (!video) return;

    let started = false;
    const onPlaying = () => {
      started = true;
    };
    video.addEventListener('playing', onPlaying);
    video.play?.().catch(() => advance());

    const guard = setTimeout(() => {
      if (!started) advance();
    }, 6000);

    return () => {
      clearTimeout(guard);
      video.removeEventListener('playing', onPlaying);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  const overlayStyle: React.CSSProperties = {
    position: 'fixed',
    inset: 0,
    background: '#000',
    zIndex: 9999,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  if (phase === 'done') {
    // 리디렉션 직전의 짧은 검정 화면
    return <div style={overlayStyle} />;
  }

  const src = phase === 'intro' ? introVideo : manualVideo;

  return (
    <div
      style={overlayStyle}
      // 2차(로딩) 비디오는 탭하면 스킵 가능
      onClick={phase === 'manual' ? advance : undefined}
    >
      <video
        key={phase}
        ref={videoRef}
        src={src ?? undefined}
        autoPlay
        muted
        playsInline
        preload="auto"
        onEnded={advance}
        onError={advance}
        style={{ width: '100vw', height: '100vh', objectFit: 'cover' }}
      />
    </div>
  );
}
