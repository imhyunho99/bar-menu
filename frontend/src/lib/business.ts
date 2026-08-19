/**
 * 전자상거래법상 사이트에 표시해야 하는 사업자 정보.
 *
 * 전자결제 심사(카카오페이 등)는 사이트 하단 정보와 사업자등록증이 글자 단위로
 * 맞는지 본다. 그래서 페이지마다 적지 않고 여기 한 곳에만 둔다.
 *
 * 빈 문자열은 '아직 못 받은 값'이라는 뜻이고, 푸터는 빈 항목을 아예 그리지 않는다.
 * 자리표시자를 넣어 두면 그대로 배포돼서 심사에 거짓 정보로 올라간다.
 * 심사 전에 businessInfoGaps() 가 비어 있는지 확인할 것.
 */
export type BusinessField = {
  readonly label: string;
  readonly value: string;
  /** 심사 필수 항목인가. 통신판매업 신고번호는 카카오페이 기준 선택이다. */
  readonly required: boolean;
};

export const BUSINESS: readonly BusinessField[] = [
  { label: '상호명', value: 'bar-menu', required: true },
  { label: '대표', value: '나현호', required: true },
  { label: '사업자등록번호', value: '102-13-82292', required: true },
  { label: '통신판매업 신고번호', value: '', required: false },
  { label: '사업장 주소', value: '', required: true },
  { label: '대표전화', value: '', required: true },
  { label: '이메일', value: '', required: true },
];

/** 화면에 그릴 항목. 값이 없는 것은 내보내지 않는다. */
export const BUSINESS_SHOWN = BUSINESS.filter((f) => f.value !== '');

/** 아직 채우지 못한 필수 항목의 이름. 심사 제출 전에 비어 있어야 한다. */
export function businessInfoGaps(): string[] {
  return BUSINESS.filter((f) => f.required && f.value === '').map((f) => f.label);
}

/** 결제·문의 회신 창구. 결제 화면의 이의신청 안내가 이 값을 쓴다. */
export const SUPPORT_EMAIL = BUSINESS.find((f) => f.label === '이메일')?.value ?? '';
export const SUPPORT_PHONE = BUSINESS.find((f) => f.label === '대표전화')?.value ?? '';
