/**
 * 미리보기라는 사실을 화면에 박아 둔다.
 *
 * 닫기 버튼을 두지 않는다. 이 바가 없으면 사장님이 이 주소를 손님에게
 * 그대로 뿌려 결제 없이 장사할 수 있고, 그때 우리는 그걸 알 방법이 없다.
 *
 * 매장 색을 따르지 않고 고정색을 쓴다. 사장님이 배경을 주황으로 칠하면
 * 이 바가 배경에 녹아 사라진다 — 녹으면 안 되는 것이 이 바의 일이다.
 */
export default function PreviewBanner() {
  return (
    <div
      role="status"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 9999,
        padding: '8px 16px',
        background: '#b45309',
        color: '#fff',
        fontSize: 13,
        lineHeight: 1.4,
        textAlign: 'center',
        letterSpacing: '-0.01em',
      }}
    >
      미리보기입니다 · 손님에게는 아직 보이지 않습니다
    </div>
  );
}
