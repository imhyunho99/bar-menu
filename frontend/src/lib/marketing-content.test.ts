import { describe, expect, it } from 'vitest';
import { FAQ, FAQ_HOME } from './marketing-content';

describe('랜딩의 자주 묻는 질문', () => {
  it('다섯 개이고, 전부 요금 페이지의 질문 목록에 있다', () => {
    // 랜딩과 요금 페이지가 다른 답을 하면 사장님은 어느 쪽을 믿어야 할지 모른다.
    expect(FAQ_HOME).toHaveLength(5);
    for (const item of FAQ_HOME) expect(FAQ).toContainEqual(item);
  });
});
