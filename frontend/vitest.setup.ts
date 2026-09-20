import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

/**
 * 렌더한 것을 테스트마다 치운다.
 *
 * @testing-library 는 globals 를 켰을 때만 이걸 스스로 건다. 여기서는
 * globals 를 끄고 vitest 를 명시적으로 import 하므로, 안 걸면 카드가
 * 화면에 쌓여서 getByText 가 "여러 개를 찾았다" 로 터진다.
 */
afterEach(cleanup);
