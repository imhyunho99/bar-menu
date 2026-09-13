import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from io import BytesIO
import base64
from PIL import Image, ImageDraw

from .admin_views import check_restaurant_permission
from .models import SiteSettings, Restaurant
from .preview import make_preview_token


@login_required
def generate_qr_code(request, restaurant_slug=None):
    # 이 뷰에는 원래 아무 검사도 없었다. 주소만 알면 누구나 남의 매장 QR 을
    # 뽑을 수 있었고, 그 QR 은 그 가게 메뉴판으로 곧장 들어간다.
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    restaurant = Restaurant.objects.filter(slug=restaurant_slug).first()
    if restaurant is None:
        raise Http404

    # 게이트(미들웨어)가 아니라 여기서 막는다. 미들웨어가 그리는 402 는 손님용
    # '준비 중' 화면인데, 이 페이지를 보는 사람은 사장님이라 무엇을 하면
    # 열리는지 알 수 없다.
    #
    # is_usable 이 아니라 menu_is_live 로 본다. 게이트가 꺼져 있으면 미결제
    # 매장의 메뉴판도 실제로 열려 있는데, 그때 QR 만 막으면 열려 있는 메뉴판을
    # 가리키는 QR 을 못 뽑는 앞뒤가 안 맞는 상태가 된다.
    subscription = getattr(restaurant, 'subscription', None)
    if subscription is None or not subscription.menu_is_live():
        return render(request, 'menu/qr_locked.html', {
            'restaurant': restaurant,
            'preview_url': (
                f'{settings.CUSTOMER_SITE_URL}/{restaurant.slug}'
                f'?preview={make_preview_token(restaurant.slug)}'
            ),
        })

    # 현재 서버 URL 가져오기
    host = request.get_host()
    protocol = 'https' if request.is_secure() else 'http'
    
    # 식당별 URL 생성 — QR 전용 진입점(주소A, /{slug}/enter/)을 가리킨다.
    if restaurant_slug:
        menu_url = f"{protocol}://{host}/{restaurant_slug}/enter/"
    else:
        # fallback (혹시 slug 없이 호출된 경우)
        menu_url = f"{protocol}://{host}/"
        
    # 사이트 설정 가져오기 및 wifi 파라미터 조건부 추가
    site_settings = None
    logo_img = None
    if restaurant_slug:
        site_settings = SiteSettings.objects.filter(restaurant__slug=restaurant_slug).first()
        if site_settings:
            if site_settings.restrict_by_wifi_ssid and site_settings.wifi_ssid:
                import urllib.parse
                menu_url = f"{menu_url}?wifi={urllib.parse.quote(site_settings.wifi_ssid)}"
            if site_settings.logo_image:
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