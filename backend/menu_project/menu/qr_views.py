import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer
from django.http import HttpResponse
from django.shortcuts import render
from io import BytesIO
import base64
from PIL import Image, ImageDraw
from .models import SiteSettings, Restaurant

from PIL import Image, ImageDraw
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
    box_size = 10
    border = 4
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(menu_url)
    qr.make(fit=True)
    
    # 3. 스타일이 적용된 이미지 생성 (데이터 점은 원형 도트 적용)
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=CircleModuleDrawer(),
        eye_drawer=CircleModuleDrawer(), # 임시로 아무 도트나 찍어둠 (어차피 아래에서 덮어씀)
        embed_image=logo_img
    )
    
    # PIL 이미지로 변환 (직접 그리기 위함)
    img_pil = img.convert("RGB")
    draw = ImageDraw.Draw(img_pil)
    
    # 4. 강제 원형 렌더링 (Force-Draw Circle Eyes)
    # 실제 생성된 QR 코드의 행/열 개수를 가져옴 (버전에 따라 다름)
    matrix_size = len(qr.modules)
    eye_positions = [
        (0, 0),                 # 좌상단
        (0, matrix_size - 7),   # 우상단
        (matrix_size - 7, 0)    # 좌하단
    ]
    
    for r, c in eye_positions:
        # 픽셀 좌표 계산 (border와 box_size 반영)
        x = (c + border) * box_size
        y = (r + border) * box_size
        width = 7 * box_size
        
        # 눈 영역을 배경색(흰색)으로 먼저 깨끗이 비움
        # (기존에 잘못 그려진 점들이나 오프셋 방지)
        draw.rectangle([x, y, x + width, y + width], fill="white")
        
        # 외곽 원형 고리 그리기
        ring_width = box_size
        draw.ellipse([x, y, x + width, y + width], outline="black", width=ring_width)
        
        # 내부 원형 점 그리기 (3x3 영역)
        dot_margin = 2 * box_size
        draw.ellipse([x + dot_margin, y + dot_margin, x + width - dot_margin, y + width - dot_margin], fill="black")

    # 이미지를 base64로 인코딩
    buffer = BytesIO()
    img_pil.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'menu/qr_code.html', {
        'qr_image': img_str,
        'menu_url': menu_url
    })