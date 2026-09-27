import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * 주소를 아는 자리는 한 곳이어야 한다.
 *
 * 운영과 dev 는 호스트가 다르다(bar-menu / develop.bar-menu,
 * api.bar-menu / devapi.bar-menu). 어딘가에 하나라도 박아 두면 그 값이
 * 반대쪽 환경으로 그대로 따라간다 — 조용히 틀리고, 틀린 줄도 모른다.
 *
 * 2026-09-27 에 실제로 그 상태였다. layout.tsx 가 /admin 접근을
 * `http://localhost:8000/admin/` 으로 보내고 있어서, 운영에서 그 주소를 연
 * 사람은 **자기 컴퓨터의** 8000 번 포트로 갔다.
 */

const SRC = join(process.cwd(), 'src');

/** 호스트를 적어도 되는 곳. 여기 말고는 없어야 한다. */
const ALLOWED = new Set([
  join(SRC, 'lib', 'site.ts'),     // appUrl — 앱 주소를 정하는 유일한 자리
  join(SRC, 'lib', 'api.ts'),      // API 주소의 로컬 기본값
  join(SRC, 'lib', 'site.test.ts'),
]);

/**
 * 주석은 뺀다. 규칙은 **코드**에 대한 것이고, 무엇이 왜 금지인지 적어 둔
 * 문장에는 그 주소가 당연히 들어간다.
 */
function codeOnly(text: string): string {
  return text
    .split('\n')
    .filter((line) => {
      const t = line.trim();
      return !t.startsWith('//') && !t.startsWith('*') && !t.startsWith('/*');
    })
    .join('\n');
}

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) return sourceFiles(full);
    return /\.(ts|tsx)$/.test(entry) ? [full] : [];
  });
}

describe('호스트를 코드에 박지 않는다', () => {
  it('localhost 주소가 새어 나온 파일이 없다', () => {
    const offenders = sourceFiles(SRC)
      .filter((file) => !ALLOWED.has(file))
      .filter((file) => /localhost:\d+/.test(codeOnly(readFileSync(file, 'utf-8'))))
      .map((file) => file.replace(SRC, 'src'));

    expect(offenders).toEqual([]);
  });

  it('dev 호스트가 박힌 파일이 없다', () => {
    const offenders = sourceFiles(SRC)
      .filter((file) => !ALLOWED.has(file))
      .filter((file) => /devapi\.bar-menu|develop\.bar-menu/.test(codeOnly(readFileSync(file, 'utf-8'))))
      .map((file) => file.replace(SRC, 'src'));

    expect(offenders).toEqual([]);
  });
});
