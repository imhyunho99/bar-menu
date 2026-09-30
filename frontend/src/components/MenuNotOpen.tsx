/**
 * 아직 열리지 않은 매장을 찾아온 손님에게 보여주는 화면.
 *
 * 결제 사정은 적지 않는다. 손님이 읽는 화면이고, 사장님이 손님 앞에서
 * 무안해질 이유가 없다. 그렇다고 404 를 띄우면 가게가 없어진 것처럼 읽히고,
 * "잠시 후 다시" 라고 하면 열릴 리 없는 화면을 계속 새로고침한다.
 */
export default function MenuNotOpen({ restaurantName }: { restaurantName?: string }) {
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
          아직 메뉴판이 준비 중입니다
        </h1>
        <p style={{ fontSize: 15, lineHeight: 1.75, color: '#6c6c74', margin: 0 }}>
          이 매장은 메뉴판을 준비하고 있습니다.
          <br />
          매장 직원에게 문의해 주세요.
        </p>
        {restaurantName && (
          <p
            style={{
              marginTop: 28,
              paddingTop: 20,
              borderTop: '1px solid #e6e6e9',
              fontSize: 12.5,
              color: '#6c6c74',
            }}
          >
            {restaurantName}
          </p>
        )}
      </div>
    </main>
  );
}
