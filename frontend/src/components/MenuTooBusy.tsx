/**
 * 지금 너무 붐벼서 잠깐 막힌 손님에게 보여주는 화면.
 *
 * MenuNotOpen 과 갈라 두는 이유: 저쪽은 '열릴 리 없으니 기다리지 마세요'
 * 이고 여기는 '곧 됩니다' 다. 둘을 한 문구로 뭉치면 잠깐 붐볐을 뿐인
 * 손님이 포기하고 나간다.
 *
 * '/' 로 보내지 않는다. QR 을 찍은 손님이 메뉴판 대신 영업 페이지를 보는
 * 것이 이 상황에서 할 수 있는 가장 나쁜 응답이다.
 */
export default function MenuTooBusy() {
  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: '#fff',
        color: '#0a0a0b',
        wordBreak: 'keep-all',
      }}
    >
      <div style={{ maxWidth: '26rem', textAlign: 'center' }}>
        <h1
          style={{
            fontSize: 21,
            fontWeight: 800,
            letterSpacing: '-0.03em',
            margin: '0 0 14px',
          }}
        >
          잠시 후 다시 열어주세요
        </h1>
        <p style={{ margin: 0, fontSize: 15, lineHeight: 1.7, color: '#6c6c74' }}>
          지금 접속이 몰려 메뉴판을 불러오지 못했습니다.
          <br />
          잠깐 기다렸다가 새로고침하시면 보입니다.
        </p>
      </div>
    </main>
  );
}
