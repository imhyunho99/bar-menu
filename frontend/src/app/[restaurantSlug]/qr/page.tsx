import QrRenderer from './QrRenderer';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '매장 QR 코드',
  description: '매장 QR 테이블 오더 스캔 페이지',
};

export default async function QrCodePage({
  params,
}: {
  params: Promise<{ restaurantSlug: string }>;
}) {
  const { restaurantSlug } = await params;

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: `
        @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@700&display=swap');

        body {
            background-color: #000 !important;
            color: #fff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        .arch-frame {
            background-color: #000;
            border: 8px solid #fff;
            border-top-left-radius: 200px;
            border-top-right-radius: 200px;
            width: 380px;
            padding: 60px 40px 40px 40px;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }

        .qr-wrapper {
            background-color: #fff;
            padding: 20px;
            border-radius: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            margin-bottom: 30px;
            margin-top: 40px;
        }

        .qr-wrapper img {
            width: 100%;
            height: auto;
            display: block;
        }

        .menu-text {
            font-family: 'Courier Prime', monospace;
            font-size: 52px;
            font-weight: 700;
            letter-spacing: 4px;
            margin-top: 10px;
            color: #fff;
            text-transform: uppercase;
        }

        @media (max-width: 480px) {
            .arch-frame {
                width: 100%;
                max-width: 320px;
                padding: 40px 30px 30px 30px;
                border-top-left-radius: 160px;
                border-top-right-radius: 160px;
            }

            .menu-text {
                font-size: 40px;
            }
        }
      ` }} />

      <div className="arch-frame">
        <div className="qr-wrapper">
          <QrRenderer slug={restaurantSlug} />
        </div>
        <div className="menu-text">MENU_</div>
      </div>
    </>
  );
}
