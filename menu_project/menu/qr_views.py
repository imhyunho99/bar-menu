import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer
from django.http import HttpResponse
from django.shortcuts import render
from io import BytesIO
import base64
from PIL import Image
from .models import SiteSettings, Restaurant

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
    
    # 1. 사이트 설정에서 로고 이미지 가져오기
    logo_img = None
    if restaurant_slug:
        site_settings = SiteSettings.objects.filter(restaurant__slug=restaurant_slug).first()
        if site_settings and site_settings.logo_image:
            try:
                logo_img = Image.open(site_settings.logo_image.path)
            except Exception:
                logo_img = None

    # 2. QR 코드 설정 (로고 삽입을 위해 Error Correction H 사용)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(menu_url)
    qr.make(fit=True)
    
    # 3. 스타일이 적용된 이미지 생성 (둥근 도트 형태)
    if logo_img:
        # 로고가 있는 경우 삽입
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=CircleModuleDrawer(),
            finder_drawer=RoundedModuleDrawer(),
            embed_image=logo_img
        )
    else:
        # 로고가 없는 경우 도트 형태만 적용
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=CircleModuleDrawer(),
            finder_drawer=RoundedModuleDrawer()
        )
    
    # 이미지를 base64로 인코딩
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'menu/qr_code.html', {
        'qr_image': img_str,
        'menu_url': menu_url
    })