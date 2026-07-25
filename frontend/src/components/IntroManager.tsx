'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';

interface IntroManagerProps {
  introVideo: string | null;
  manualVideo: string | null;
  showManualCard: boolean;
  /**
   * 메뉴 진입 시 인트로 비디오를 자동재생할지 여부. 기본 true(기존 동작).
   * 주소A(enter)로 진입 비디오를 옮긴 뒤로, 메뉴판(주소B)에서는 false로 넘겨
   * 자동재생을 끄되 "메뉴판 설명서" 수동 카드 기능은 그대로 유지한다.
   */
  autoPlayIntro?: boolean;
}

export default function IntroManager({ introVideo, manualVideo, showManualCard, autoPlayIntro = true }: IntroManagerProps) {
  const [showIntro, setShowIntro] = useState(false);
  const [activeVideo, setActiveVideo] = useState<'intro' | 'manual' | null>(null);
  const [doorOpen, setDoorOpen] = useState(false);

  const introVideoRef = useRef<HTMLVideoElement>(null);
  const manualVideoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!autoPlayIntro) return;
    if (!introVideo) return;

    const lastIntroTime = localStorage.getItem('lastIntroTime');
    const currentTime = Date.now();
    const oneHour = 60 * 60 * 1000;

    if (lastIntroTime && (currentTime - parseInt(lastIntroTime)) < oneHour) {
      // 1시간 이내에 시청한 경우 생략
      return;
    }

    // 시청 시간 기록 및 인트로 활성화
    localStorage.setItem('lastIntroTime', currentTime.toString());
    setShowIntro(true);
    setActiveVideo('intro');

    // 비디오 자동 재생 실패 대비용 폴백 타이머 (5초 후 강제 종료)
    const fallback = setTimeout(() => {
      handleIntroEnd();
    }, 5000);

    return () => clearTimeout(fallback);
  }, [introVideo, autoPlayIntro]);

  const handleIntroEnd = () => {
    if (manualVideo) {
      // 매뉴얼 비디오가 있으면 2차 비디오로 전환
      setActiveVideo('manual');
      setTimeout(() => {
        manualVideoRef.current?.play().catch(() => {
          finishIntro();
        });
      }, 50);
    } else {
      finishIntro();
    }
  };

  const finishIntro = () => {
    setDoorOpen(true);
    setTimeout(() => {
      setShowIntro(false);
      setActiveVideo(null);
    }, 500);
  };

  const playManualVideoDirect = () => {
    setShowIntro(true);
    setActiveVideo('manual');
    setDoorOpen(false);
    setTimeout(() => {
      if (manualVideoRef.current) {
        manualVideoRef.current.currentTime = 0;
        manualVideoRef.current.play().catch(() => {
          finishIntro();
        });
      }
    }, 50);
  };

  const handleManualVideoClick = () => {
    if (activeVideo === 'manual') {
      finishIntro();
    }
  };

  return (
    <>
      {/* 메뉴판 설명서 카드 */}
      {showManualCard && manualVideo && (
        <button className="category-card manual-card" onClick={playManualVideoDirect} style={{ width: '100%', border: 'none', background: 'transparent', textAlign: 'center', cursor: 'pointer' }}>
          <p className="category-name-en">Menu Guide</p>
          <h3 className="category-name-ko">메뉴판 설명서</h3>
        </button>
      )}

      {/* 인트로 overlay 비디오 */}
      {showIntro && (
        <div
          id="loading-screen"
          className={`loading-screen ${doorOpen ? 'door-open' : ''}`}
          onClick={handleManualVideoClick}
        >
          <div className="loading-logo">
            {introVideo && activeVideo === 'intro' && (
              <video
                ref={introVideoRef}
                autoPlay
                muted
                playsInline
                preload="metadata"
                onEnded={handleIntroEnd}
                onError={handleIntroEnd}
                onPlay={(e) => {
                  // 재생 시작 시 폴백 제거하기 위해 상위 useEffect에서 제어
                }}
                style={{ width: '100vw', height: '100vh', objectFit: 'cover' }}
              >
                <source src={introVideo} type="video/mp4" />
                <Image src="/logo.png" alt="Logo" width={400} height={400} style={{ width: '80vw', maxWidth: '400px', height: 'auto' }} />
              </video>
            )}

            {manualVideo && activeVideo === 'manual' && (
              <video
                ref={manualVideoRef}
                muted
                playsInline
                preload="metadata"
                onEnded={finishIntro}
                onError={finishIntro}
                onClick={finishIntro}
                style={{ width: '100vw', height: '100vh', objectFit: 'cover' }}
              >
                <source src={manualVideo} type="video/mp4" />
              </video>
            )}
          </div>
        </div>
      )}
    </>
  );
}
