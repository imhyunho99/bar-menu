import { render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import IntroManager from './IntroManager';

/**
 * 인트로 영상은 한 시간에 한 번만 나온다.
 *
 * 손님이 메뉴를 보다 QR 을 다시 찍을 때마다 영상이 처음부터 재생되면
 * 성가시다. 그래서 사장님이 1시간 규칙을 넣어 뒀는데, 2026-07 에 영상을
 * /<slug>/enter 로 옮기면서 **쿨다운이 따라가지 않았다** — 그쪽은 자체
 * 플레이어를 들고 있었고 localStorage 를 건드리지 않았다.
 *
 * 코드는 IntroManager 안에 그대로 남아 있었지만 `autoPlayIntro` 가 꺼져
 * 있어 그 함수에 아예 들어가지 않았다. '있는데 안 도는' 상태라 눈으로는
 * 안 보였다. 2026-10-01 운영에서 영상이 매번 재생되는 것으로 드러났다.
 */

const KEY = 'lastIntroTime';
const HOUR = 60 * 60 * 1000;

function draw(props: Partial<React.ComponentProps<typeof IntroManager>> = {}) {
  return render(
    <IntroManager
      introVideo="https://example.test/intro.mp4"
      manualVideo={null}
      showManualCard={false}
      {...props}
    />,
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-10-01T19:00:00+09:00'));
});

afterEach(() => {
  vi.useRealTimers();
});

describe('인트로 1시간 쿨다운', () => {
  it('처음 온 손님에게는 보여주고 본 시각을 적어 둔다', () => {
    const { container } = draw();
    expect(localStorage.getItem(KEY)).not.toBeNull();
    expect(container.querySelector('video')).toBeTruthy();
  });

  it('한 시간 안에 다시 오면 안 보여준다', () => {
    localStorage.setItem(KEY, String(Date.now() - 30 * 60 * 1000));
    const { container } = draw();
    expect(container.querySelector('video')).toBeNull();
  });

  it('한 시간이 지나면 다시 보여준다', () => {
    localStorage.setItem(KEY, String(Date.now() - HOUR - 1000));
    const { container } = draw();
    expect(container.querySelector('video')).toBeTruthy();
  });

  it('다시 보여줄 때 본 시각을 새로 적는다', () => {
    const old = String(Date.now() - HOUR - 1000);
    localStorage.setItem(KEY, old);
    draw();
    expect(localStorage.getItem(KEY)).not.toBe(old);
  });

  it('영상이 없는 매장은 아무 일도 안 한다', () => {
    const { container } = draw({ introVideo: null });
    expect(container.querySelector('video')).toBeNull();
    expect(localStorage.getItem(KEY)).toBeNull();
  });
});

describe('쿨다운이 꺼지지 않는다', () => {
  it('손님 화면은 autoPlayIntro 를 끄지 않는다', async () => {
    /**
     * 여기가 이번에 당한 자리다. autoPlayIntro 를 끄면 쿨다운 코드가 통째로
     * 건너뛰어지고, 영상도 안 나온다. 끄려면 이 테스트를 지워야 하므로
     * 그때는 적어도 무엇을 포기하는지 보고 지우게 된다.
     */
    const { readFileSync } = await import('node:fs');
    const { join } = await import('node:path');
    const page = readFileSync(
      join(process.cwd(), 'src/app/[restaurantSlug]/page.tsx'), 'utf-8',
    );
    const code = page.split('\n').filter((l) => {
      const t = l.trim();
      return !t.startsWith('//') && !t.startsWith('*') && !t.startsWith('/*');
    }).join('\n');

    expect(code).toMatch(/<IntroManager/);
    expect(code).not.toMatch(/autoPlayIntro=\{false\}/);
  });
});
