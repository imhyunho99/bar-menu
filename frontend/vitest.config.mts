import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

/**
 * 프론트 단위 테스트.
 *
 * 그동안 프론트 계약을 Django 테스트가 **소스를 문자열로 뒤져서** 확인했다.
 * 함수 이름만 바꿔도 테스트는 통과하고 기능은 죽는 방식이라, 레이아웃처럼
 * 조건 분기가 있는 코드에는 위험하다.
 *
 * async 서버 컴포넌트는 vitest 가 아직 못 돈다(Next 문서 명시). 그건 계속
 * 브라우저 E2E 로 본다.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    // vite-tsconfig-paths 플러그인은 뺐다. Vite 가 같은 일을 내장으로 한다고
    // 실행할 때마다 알려 준다.
    tsconfigPaths: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
