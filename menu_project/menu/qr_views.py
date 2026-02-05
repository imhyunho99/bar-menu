import qrcode
from django.http import HttpResponse
from django.shortcuts import render
from io import BytesIO
import base64

def generate_qr_code(request, restaurant_slug=None):
    # 현재 서버 URL 가져오기
    host = request.get_host()
    protocol = 'https' if request.is_secure() else 'http'
    
    # 식당별 URL 생성
    if restaurant_slug:
        menu_url = f"{protocol}://{host}/{restaurant_slug}/"
    else:
        # fallback (혹시 slug 없이 호출된 경우)
        menu_url = f"{protocol}://{host}/"
    
    # QR 코드 생성
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(menu_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 이미지를 base64로 인코딩
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'menu/qr_code.html', {
        'qr_image': img_str,
        'menu_url': menu_url
    })