'use client';

import { useEffect } from 'react';
import { useRestaurant } from '@/app/[restaurantSlug]/context';

export default function ScreenshotBlocker() {
  const { restaurant } = useRestaurant();
  const settings = restaurant.site_settings;

  useEffect(() => {
    if (!settings || !settings.disable_screenshots) return;

    // 1. 우클릭 방지
    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault();
    };

    // 2. 드래그 선택 방지
    const handleSelectStart = (e: Event) => {
      e.preventDefault();
    };

    // 3. 캡쳐 단축키 및 단축 기능 방지
    const handleKeyDown = (e: KeyboardEvent) => {
      // PrintScreen 키 입력 시 클립보드 강제 초기화
      if (e.key === 'PrintScreen' || e.keyCode === 44) {
        if (navigator.clipboard) {
          navigator.clipboard.writeText('보안정책으로 캡쳐할 수 없습니다.');
        }
        alert('스크린샷 캡쳐가 제한된 매장 보안 페이지입니다.');
      }

      // Ctrl + P, Cmd + P (인쇄/PDF 저장 차단)
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        alert('인쇄 및 화면 PDF 저장이 제한되어 있습니다.');
      }

      // Ctrl + S, Cmd + S (소스 저장 차단)
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
      }

      // 개발자 도구 차단 (F12, Cmd+Opt+I, Ctrl+Shift+I 등)
      if (
        e.key === 'F12' ||
        ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'i') ||
        ((e.ctrlKey || e.metaKey) && e.altKey && e.key.toLowerCase() === 'i')
      ) {
        e.preventDefault();
      }
    };

    // 4. 모바일 및 PC 인쇄 기능 시도 시 화면 흐리게 처리(Blur) 및 복구
    const handleBeforePrint = () => {
      document.body.style.filter = 'blur(20px)';
    };
    const handleAfterPrint = () => {
      document.body.style.filter = 'none';
    };

    // 이벤트 리스너 등록
    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('selectstart', handleSelectStart);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('beforeprint', handleBeforePrint);
    window.addEventListener('afterprint', handleAfterPrint);

    // CSS 강제 주입: 스크린샷 툴이나 인쇄 시 텍스트 드래그 금지 및 인쇄 시 완전 숨김
    const styleEl = document.createElement('style');
    styleEl.innerHTML = `
      body {
        -webkit-touch-callout: none !important;
        -webkit-user-select: none !important;
        -khtml-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
      }
      @media print {
        body {
          display: none !important;
          opacity: 0 !important;
        }
      }
    `;
    document.head.appendChild(styleEl);

    // 정리(Cleanup)
    return () => {
      document.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('selectstart', handleSelectStart);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('beforeprint', handleBeforePrint);
      window.removeEventListener('afterprint', handleAfterPrint);
      document.head.removeChild(styleEl);
    };
  }, [settings]);

  return null;
}
