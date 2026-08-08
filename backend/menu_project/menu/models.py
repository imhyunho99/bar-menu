# menu/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .utils import optimize_image

class Restaurant(models.Model):
    """
    개별 가게(Restaurant) 모델
    - Multi-tenancy의 핵심 단위
    - 서브도메인(slug)으로 식별
    """
    name = models.CharField(max_length=100, verbose_name="가게 이름")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="서브도메인 ID")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.slug})"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, blank=True, related_name='managers')
    
    def __str__(self):
        return f"{self.user.username} - {self.restaurant.name if self.restaurant else 'No Restaurant'}"

# User 관련 시그널 제거됨 (Admin Inline 충돌 방지)

@receiver(post_save, sender=Restaurant)
def create_restaurant_settings(sender, instance, created, **kwargs):
    if created:
        SiteSettings.objects.create(restaurant=instance)

def default_category_layout():
    return {
        "layout_type": "default",
        "components": [
            {"id": "category_image", "name": "카테고리 이미지", "visible": True, "x": 0, "y": 0, "w": 100, "h": 65},
            {"id": "category_name", "name": "카테고리명 (한글)", "visible": True, "x": 5, "y": 70, "w": 90, "h": 15},
            {"id": "category_name_en", "name": "카테고리명 (영문)", "visible": True, "x": 5, "y": 85, "w": 90, "h": 10}
        ]
    }

def default_menu_layout():
    return {
        "layout_type": "default",
        "components": [
            {"id": "menu_image", "name": "메뉴 이미지", "visible": True, "x": 0, "y": 0, "w": 100, "h": 50},
            {"id": "menu_name", "name": "메뉴명 (한글)", "visible": True, "x": 5, "y": 55, "w": 90, "h": 12},
            {"id": "menu_name_en", "name": "메뉴명 (영문)", "visible": True, "x": 5, "y": 68, "w": 90, "h": 8},
            {"id": "menu_price", "name": "가격", "visible": True, "x": 5, "y": 78, "w": 90, "h": 10},
            {"id": "menu_description", "name": "메뉴 설명", "visible": True, "x": 5, "y": 89, "w": 90, "h": 10}
        ]
    }

class SiteSettings(models.Model):
    """
    사이트 설정 모델 - 인트로 이미지 등을 관리
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='site_settings', null=True, blank=True)
    logo_image = models.ImageField(
        upload_to='site_images/',
        blank=True,
        null=True,
        verbose_name="로고 이미지",
        help_text="파비콘(Favicon)으로 사용될 로고 이미지"
    )
    intro_image = models.ImageField(
        upload_to='site_images/',
        blank=True,
        null=True,
        verbose_name="인트로 이미지",
        help_text="메인 페이지에 표시될 인트로 이미지"
    )
    intro_video = models.FileField(
        upload_to='site_videos/',
        blank=True,
        null=True,
        verbose_name="로딩 비디오",
        help_text="첫 번째로 표시될 로딩 비디오 (MP4 파일)"
    )
    loading_video_2 = models.FileField(
        upload_to='site_videos/',
        blank=True,
        null=True,
        verbose_name="로딩 비디오2",
        help_text="첫 번째 로딩 비디오 이후 재생될 두 번째 로딩 비디오 (화면 터치 시 스킵 가능)"
    )
    show_manual_card = models.BooleanField(
        default=False,
        verbose_name="메뉴 설명서 카드 표시",
        help_text="체크 시 메인 화면(인트로 이미지 밑)에 두 번째 로딩 비디오와 동일한 영상을 보여주는 카드가 표시됩니다."
    )
    side_image = models.ImageField(
        upload_to='site_images/',
        blank=True,
        null=True,
        verbose_name="사이드 이미지",
        help_text="사이드 메뉴 등에 사용될 이미지"
    )
    
    # WiFi 및 결제 설정
    wifi_ssid = models.CharField(max_length=100, blank=True, null=True, verbose_name="WiFi SSID")
    wifi_password = models.CharField(max_length=100, blank=True, null=True, verbose_name="WiFi 비밀번호")
    wifi_security = models.CharField(
        max_length=20, 
        default='WPA', 
        choices=[('WPA', 'WPA/WPA2'), ('WEP', 'WEP'), ('nopass', 'Open')],
        verbose_name="WiFi 보안 설정"
    )
    enable_wifi = models.BooleanField(default=False, verbose_name="WiFi 안내 활성화")
    enable_payhere = models.BooleanField(default=False, verbose_name="페이히어 결제 활성화")
    enable_cart = models.BooleanField(
        default=False, 
        verbose_name="장바구니 활성화", 
        help_text="체크 시 고객 메뉴판 사이트에서 장바구니 추가 버튼 및 장바구니 버튼이 표시됩니다."
    )
    payhere_store_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="페이히어 상점 ID")
    payhere_api_key = models.CharField(max_length=200, blank=True, null=True, verbose_name="페이히어 API Key", help_text="페이히어 POS 연동 API Key")
    store_public_ip = models.CharField(max_length=100, blank=True, null=True, verbose_name="매장 공인 IP 주소", help_text="매장의 공인 IP 주소 (예: 123.45.67.89)")
    restrict_by_ip = models.BooleanField(default=False, verbose_name="매장 WiFi(IP) 접속 제한 활성화", help_text="체크 시 설정된 매장 공인 IP에서 접속하지 않은 고객의 접속을 제한합니다.")
    restrict_by_wifi_ssid = models.BooleanField(default=False, verbose_name="매장 WiFi SSID 접속 제한 활성화", help_text="체크 시 테이블 QR 코드로 접속하지 않았거나 매장 와이파이 SSID 정보가 다르면 접속을 제한합니다.")
    disable_screenshots = models.BooleanField(default=False, verbose_name="스크린샷 금지 활성화", help_text="활성화 시 고객 메뉴판 사이트에서 스크린샷 및 화면 캡쳐(프린트 등)를 방지합니다.")

    background_color = models.CharField(
        max_length=20, 
        default='#000000', 
        verbose_name="배경색", 
        help_text="사이트 배경색 (예: #000000)"
    )

    category_card_color = models.CharField(
        max_length=20,
        default='#000000',
        verbose_name="카테고리 카드 배경색",
        help_text="카테고리 목록 카드의 배경색 (예: #000000)"
    )

    menu_card_color = models.CharField(
        max_length=20,
        default='#000000',
        verbose_name="메뉴 카드 배경색",
        help_text="메뉴 상세 항목의 배경색 (예: #000000)"
    )
    
    # 메뉴명(한글) 설정
    menu_name_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="메뉴명(한글) 폰트 파일")
    menu_name_color = models.CharField(max_length=7, blank=True, default='', verbose_name="메뉴명(한글) 색상", help_text="#ffffff")
    menu_name_size = models.IntegerField(blank=True, null=True, verbose_name="메뉴명(한글) 크기", help_text="픽셀 단위 (예: 18)")
    menu_name_bold = models.BooleanField(default=False, verbose_name="메뉴명(한글) 볼드")
    menu_name_italic = models.BooleanField(default=False, verbose_name="메뉴명(한글) 이탤릭")
    
    # 메뉴명(영문) 설정
    menu_name_en_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="메뉴명(영문) 폰트 파일")
    menu_name_en_color = models.CharField(max_length=7, blank=True, default='', verbose_name="메뉴명(영문) 색상", help_text="#cccccc")
    menu_name_en_size = models.IntegerField(blank=True, null=True, verbose_name="메뉴명(영문) 크기", help_text="픽셀 단위 (예: 14)")
    menu_name_en_bold = models.BooleanField(default=False, verbose_name="메뉴명(영문) 볼드")
    menu_name_en_italic = models.BooleanField(default=False, verbose_name="메뉴명(영문) 이탤릭")
    
    # 가격 설정
    menu_price_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="가격 폰트 파일")
    menu_price_color = models.CharField(max_length=7, blank=True, default='', verbose_name="가격 색상", help_text="#ffffff")
    menu_price_size = models.IntegerField(blank=True, null=True, verbose_name="가격 크기", help_text="픽셀 단위 (예: 20)")
    menu_price_bold = models.BooleanField(default=False, verbose_name="가격 볼드")
    menu_price_italic = models.BooleanField(default=False, verbose_name="가격 이탤릭")
    
    # 메뉴 설명 설정
    menu_description_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="메뉴 설명 폰트 파일")
    menu_description_color = models.CharField(max_length=7, blank=True, default='', verbose_name="메뉴 설명 색상", help_text="#aaaaaa")
    menu_description_size = models.IntegerField(blank=True, null=True, verbose_name="메뉴 설명 크기", help_text="픽셀 단위 (예: 14)")
    menu_description_bold = models.BooleanField(default=False, verbose_name="메뉴 설명 볼드")
    menu_description_italic = models.BooleanField(default=False, verbose_name="메뉴 설명 이탤릭")

    # 기타 사항 설정
    menu_notes_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="기타 사항 폰트 파일")
    menu_notes_color = models.CharField(max_length=7, blank=True, default='', verbose_name="기타 사항 색상", help_text="#888888")
    menu_notes_size = models.IntegerField(blank=True, null=True, verbose_name="기타 사항 크기", help_text="픽셀 단위 (예: 12)")
    menu_notes_bold = models.BooleanField(default=False, verbose_name="기타 사항 볼드")
    menu_notes_italic = models.BooleanField(default=False, verbose_name="기타 사항 이탤릭")
    
    # 카테고리명(한글) 설정
    category_name_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="카테고리명(한글) 폰트 파일")
    category_name_color = models.CharField(max_length=7, blank=True, default='', verbose_name="카테고리명(한글) 색상", help_text="#ffffff")
    category_name_size = models.IntegerField(blank=True, null=True, verbose_name="카테고리명(한글) 크기", help_text="픽셀 단위 (예: 18)")
    category_name_bold = models.BooleanField(default=False, verbose_name="카테고리명(한글) 볼드")
    category_name_italic = models.BooleanField(default=False, verbose_name="카테고리명(한글) 이탤릭")
    
    # 카테고리명(영문) 설정
    category_name_en_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="카테고리명(영문) 폰트 파일")
    category_name_en_color = models.CharField(max_length=7, blank=True, default='', verbose_name="카테고리명(영문) 색상", help_text="#cccccc")
    category_name_en_size = models.IntegerField(blank=True, null=True, verbose_name="카테고리명(영문) 크기", help_text="픽셀 단위 (예: 14)")
    category_name_en_bold = models.BooleanField(default=False, verbose_name="카테고리명(영문) 볼드")
    category_name_en_italic = models.BooleanField(default=False, verbose_name="카테고리명(영문) 이탤릭")
    
    # 추천 페어링명 설정
    pairing_name_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="페어링명 폰트 파일")
    pairing_name_color = models.CharField(max_length=7, blank=True, default='', verbose_name="페어링명 색상", help_text="#ffffff")
    pairing_name_size = models.IntegerField(blank=True, null=True, verbose_name="페어링명 크기", help_text="픽셀 단위 (예: 14)")
    pairing_name_bold = models.BooleanField(default=False, verbose_name="페어링명 볼드")
    pairing_name_italic = models.BooleanField(default=False, verbose_name="페어링명 이탤릭")

    # 추천 페어링 설명 설정
    pairing_description_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="페어링 설명 폰트 파일")
    pairing_description_color = models.CharField(max_length=7, blank=True, default='', verbose_name="페어링 설명 색상", help_text="#888888")
    pairing_description_size = models.IntegerField(blank=True, null=True, verbose_name="페어링 설명 크기", help_text="픽셀 단위 (예: 11)")
    pairing_description_bold = models.BooleanField(default=False, verbose_name="페어링 설명 볼드")
    pairing_description_italic = models.BooleanField(default=False, verbose_name="페어링 설명 이탤릭")

    # 추천 페어링 가격 설정
    pairing_price_font = models.FileField(upload_to='fonts/', blank=True, null=True, verbose_name="페어링 가격 폰트 파일")
    pairing_price_color = models.CharField(max_length=7, blank=True, default='', verbose_name="페어링 가격 색상", help_text="#ffffff")
    pairing_price_size = models.IntegerField(blank=True, null=True, verbose_name="페어링 가격 크기", help_text="픽셀 단위 (예: 12)")
    pairing_price_bold = models.BooleanField(default=False, verbose_name="페어링 가격 볼드")
    pairing_price_italic = models.BooleanField(default=False, verbose_name="페어링 가격 이탤릭")
    
    category_card_layout_json = models.JSONField(
        default=default_category_layout,
        blank=True,
        verbose_name="카테고리 카드 레이아웃 JSON",
        help_text="카테고리 카드의 컴포넌트 배치 및 보임 설정 JSON"
    )
    menu_card_layout_json = models.JSONField(
        default=default_menu_layout,
        blank=True,
        verbose_name="메뉴 카드 레이아웃 JSON",
        help_text="메뉴 카드의 컴포넌트 배치 및 보임 설정 JSON"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "사이트 설정"
        verbose_name_plural = "사이트 설정"

    def __str__(self):
        return f"사이트 설정 - {self.created_at.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        if self.logo_image:
            self.logo_image = optimize_image(self.logo_image, max_width=192, quality=90)
        if self.intro_image:
            self.intro_image = optimize_image(self.intro_image, max_width=1200, quality=85)
        if self.side_image:
            self.side_image = optimize_image(self.side_image, max_width=800, quality=85)
        super().save(*args, **kwargs)

class Category(models.Model):
    """
    메뉴 카테고리 모델. 부모-자식 관계를 통해 계층 구조를 지원합니다.
    (예: 음료 > 커피 > 아이스 아메리카노)
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="카테고리명(한글)", blank=True)
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="카테고리명(영문)")
    priority = models.FloatField(
        default=0.0,
        verbose_name="우선순위",
        help_text="낮은 숫자일수록 먼저 표시됩니다"
    )
    # 'self'를 참조하여 부모 카테고리를 지정할 수 있습니다.
    # 최상위 카테고리(부모 카테고리)는 이 필드가 비어있게 됩니다.
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_categories',
        verbose_name="부모 카테고리"
    )
    # 카테고리 이미지 필드 추가
    category_image = models.ImageField(
        upload_to='category_images/',
        blank=True,
        null=True,
        verbose_name="카테고리 이미지"
    )
    # 사이드 이미지 숨김 여부
    hide_side_image = models.BooleanField(
        default=False,
        verbose_name="사이드 이미지 숨기기",
        help_text="체크하면 이 카테고리에서 배경 이미지가 뒤로 숨겨집니다"
    )

    class Meta:
        verbose_name = "메뉴 카테고리"
        verbose_name_plural = "메뉴 카테고리"
        ordering = ['priority', 'name']

    def __str__(self):
        # 부모 카테고리가 있는 경우 '부모 > 자식' 형태로 표시
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        if self.category_image:
            self.category_image = optimize_image(self.category_image, max_width=600, quality=80)
        super().save(*args, **kwargs)

class MenuItem(models.Model):
    """
    개별 메뉴 항목에 대한 모델
    """
    # 표시 모드 선택지
    DISPLAY_MODE_CHOICES = [
        ('auto', '자동 (이미지 있으면 이미지만, 없으면 텍스트만)'),
        ('image_only', '이미지만 표시'),
        ('text_only', '텍스트만 표시'),
        ('combined', '이미지 + 텍스트 (좌측 이미지, 우측 텍스트)'),
    ]

    # 라이트박스 스타일 선택지
    LIGHTBOX_STYLE_CHOICES = [
        ('zoom', '확대 (기본) — 이미지가 중앙에서 확대됩니다'),
        ('slide_up', '슬라이드 — 아래에서 위로 올라옵니다'),
        ('fade', '페이드 — 서서히 나타납니다'),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items', null=True, blank=True)
    # 1. 이름 (여러 줄 지원을 위해 TextField로 변경)
    name = models.TextField(verbose_name="메뉴명")
    
    # 2. 영문명 (여러 줄 지원을 위해 TextField로 변경)
    name_en = models.TextField(blank=True, null=True, verbose_name="메뉴명(영문)")

    # 3. 가격
    price = models.TextField(verbose_name="가격", help_text="가격을 입력하세요 (예: 15000, 15.5, 15,000)")

    # 3. 설명 (선택 사항으로 변경)
    description = models.TextField(blank=True, null=True, verbose_name="메뉴 설명")

    # 4. 카테고리 (부모/서브 카테고리)
    # Category 모델과 연결하여 메뉴의 소속 카테고리를 지정합니다.
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL, # 카테고리가 삭제되어도 메뉴는 유지 (카테고리 없음 상태로)
        null=True,
        blank=True,
        related_name='menu_items',
        verbose_name="카테고리"
    )

    # 5. 기타
    notes = models.TextField(blank=True, null=True, verbose_name="기타 사항")

    # 6. 메뉴 이미지
    menu_image = models.ImageField(
        upload_to='menu_images/',
        blank=True,
        null=True,
        verbose_name="메뉴 이미지"
    )

    # 7. 우선순위
    priority = models.FloatField(
        default=0.0,
        verbose_name="우선순위",
        help_text="낮은 숫자일수록 먼저 표시됩니다"
    )
    
    is_available = models.BooleanField(default=True, verbose_name="판매 가능 여부")

    # 8. 표시 모드 (플랜 2-2)
    display_mode = models.CharField(
        max_length=20,
        choices=DISPLAY_MODE_CHOICES,
        default='auto',
        verbose_name="표시 모드",
        help_text="메뉴 카드의 표시 방식을 선택합니다"
    )

    # 9. 이미지 클릭 확대 (플랜 2-2)
    click_expand = models.BooleanField(
        default=False,
        verbose_name="이미지 클릭 확대",
        help_text="체크하면 이미지 클릭 시 라이트박스로 확대됩니다"
    )

    # 9-1. 라이트박스 스타일 선택
    lightbox_style = models.CharField(
        max_length=20,
        choices=LIGHTBOX_STYLE_CHOICES,
        default='zoom',
        verbose_name="라이트박스 스타일",
        help_text="이미지 확대 시 애니메이션 스타일을 선택합니다"
    )

    # 9-2. 라이트박스 및 모달 배경 투명도 (%)
    lightbox_opacity = models.IntegerField(
        default=35,
        verbose_name="라이트박스 투명도 (%)",
        help_text="배경 오버레이의 투명도(불투명도)를 설정합니다 (10% ~ 100%)"
    )

    # 10. 상세보기 활성화 (플랜 2-1)
    enable_detail_view = models.BooleanField(
        default=False,
        verbose_name="상세보기 활성화",
        help_text="체크하면 메뉴 클릭 시 상세 정보 모달이 표시됩니다"
    )

    # 11. 상세보기 전용 이미지 (플랜 2-1)
    detail_image = models.ImageField(
        upload_to='menu_images/detail/',
        blank=True,
        null=True,
        verbose_name="상세보기 이미지",
        help_text="상세 모달에 표시될 이미지 (미설정 시 기본 메뉴 이미지 사용)"
    )

    # 12. 메뉴 세부 설명
    detail_description = models.TextField(
        blank=True,
        null=True,
        verbose_name="메뉴 세부 설명",
        help_text="상세 모달(라이트박스)에 표시될 메뉴 세부 설명 및 주류 페어링 정보 (미설정 시 표시되지 않음)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    class Meta:
        verbose_name = "메뉴 항목"
        verbose_name_plural = "메뉴 항목"
        ordering = ['priority', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.menu_image:
            self.menu_image = optimize_image(self.menu_image, max_width=800, quality=80)
        if self.detail_image:
            self.detail_image = optimize_image(self.detail_image, max_width=1200, quality=85)
        super().save(*args, **kwargs)


class MenuItemPairing(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='pairings', verbose_name="메뉴 항목")
    name = models.CharField(max_length=100, verbose_name="주류 이름")
    image = models.ImageField(upload_to='pairing_images/', blank=True, null=True, verbose_name="주류 이미지")
    description = models.TextField(blank=True, null=True, verbose_name="주류 간단 설명")
    price = models.CharField(max_length=50, blank=True, null=True, verbose_name="주류 가격")
    priority = models.IntegerField(default=0, verbose_name="우선순위")

    class Meta:
        verbose_name = "추천 페어링"
        verbose_name_plural = "추천 페어링"
        ordering = ['priority', 'id']

    def __str__(self):
        return f"{self.menu_item.name} - {self.name}"

    def save(self, *args, **kwargs):
        if self.image:
            self.image = optimize_image(self.image, max_width=300, quality=80)
        super().save(*args, **kwargs)


class Subscription(models.Model):
    """
    매장 하나의 구독 상태.

    결제 대행사는 아직 안 붙었다. 그래서 이 모델은 '누가 언제까지 쓸 수
    있는가'만 알고, 돈을 걷는 방법은 모른다. 대행사가 붙을 때 채울 자리는
    provider_* 세 필드뿐이고 나머지 상태 기계는 그대로 쓴다.
    """

    PLAN_CHOICES = [
        ('entry', 'Entry'),
        ('pro', 'Pro'),
        ('premium', 'Premium'),
    ]

    # trialing  : 무료 체험 중. 손님 화면 정상 노출
    # active    : 결제까지 정상
    # past_due  : 결제 실패. 유예 기간 동안은 계속 열어 둔다
    # canceled  : 해지됨. 체험 만료도 여기로 온다
    STATUS_CHOICES = [
        ('trialing', '무료 체험'),
        ('active', '이용 중'),
        ('past_due', '결제 실패'),
        ('canceled', '해지'),
    ]

    TRIAL_DAYS = 14

    restaurant = models.OneToOneField(
        Restaurant, on_delete=models.CASCADE, related_name='subscription', verbose_name="매장"
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='entry', verbose_name="요금제")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing', verbose_name="상태")

    trial_ends_at = models.DateTimeField(null=True, blank=True, verbose_name="체험 종료")
    # 결제가 붙으면 대행사가 알려주는 다음 결제일. 그 전까지는 비어 있다.
    current_period_end = models.DateTimeField(null=True, blank=True, verbose_name="이번 결제 주기 종료")
    canceled_at = models.DateTimeField(null=True, blank=True, verbose_name="해지 시각")

    # ── 결제 대행사가 붙을 때 채우는 자리 ──────────────────────────
    # 어느 대행사인지는 여기 문자열로만 남긴다. 코드가 특정 회사를 알지
    # 않도록 실제 호출은 menu/billing/ 의 provider 가 맡는다.
    provider = models.CharField(max_length=30, blank=True, default='', verbose_name="결제 대행사")
    provider_customer_id = models.CharField(max_length=200, blank=True, default='', verbose_name="대행사 고객 ID")
    provider_subscription_id = models.CharField(max_length=200, blank=True, default='', verbose_name="대행사 구독 ID")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "구독"
        verbose_name_plural = "구독 목록"

    def __str__(self):
        return f"{self.restaurant.name} · {self.get_plan_display()} ({self.get_status_display()})"

    @property
    def access_until(self):
        """언제까지 열어 둘지. 결제가 붙기 전에는 체험 종료일이 곧 그 날이다."""
        return self.current_period_end or self.trial_ends_at

    @property
    def days_left(self):
        from django.utils import timezone

        until = self.access_until
        if until is None:
            return None
        return max(0, (until - timezone.now()).days)

    def is_usable(self):
        """
        손님에게 메뉴판을 보여줘도 되는 상태인가.

        past_due 를 열어 두는 건 의도적이다. 카드 한 번 실패했다고 영업
        중인 가게의 메뉴판을 꺼버리면 그게 더 큰 사고다.
        """
        from django.utils import timezone

        if self.status == 'canceled':
            return False
        if self.status == 'past_due':
            return True
        until = self.access_until
        return until is None or until > timezone.now()

    def start_trial(self, days=None):
        from datetime import timedelta

        from django.utils import timezone

        self.status = 'trialing'
        self.trial_ends_at = timezone.now() + timedelta(days=days or self.TRIAL_DAYS)
        return self


class ContactSubmission(models.Model):
    name = models.CharField(max_length=100, verbose_name="이름(업체명)")
    contact_info = models.CharField(max_length=200, verbose_name="연락처 또는 이메일")
    plan = models.CharField(max_length=50, default='general', verbose_name="선택 요금제")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="접수 일시")

    class Meta:
        verbose_name = "제휴 문의"
        verbose_name_plural = "제휴 문의 목록"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.contact_info}) - {self.plan}"


class Order(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders', verbose_name="가게")
    table_number = models.CharField(max_length=50, default='테이블', verbose_name="테이블 번호")
    status = models.CharField(
        max_length=20, 
        choices=[('pending', '대기 중'), ('completed', '완료됨'), ('cancelled', '취소됨')], 
        default='pending',
        verbose_name="주문 상태"
    )
    total_price = models.IntegerField(default=0, verbose_name="총 결제금액")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="주문 시간")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="변경 시간")

    class Meta:
        verbose_name = "주문"
        verbose_name_plural = "주문 목록"
        ordering = ['-created_at']

    def __str__(self):
        return f"주문 #{self.id} - 테이블 {self.table_number} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="주문")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="메뉴")
    name = models.CharField(max_length=200, verbose_name="메뉴명")
    price = models.IntegerField(default=0, verbose_name="가격")
    quantity = models.IntegerField(default=1, verbose_name="수량")

    class Meta:
        verbose_name = "주문 상세 항목"
        verbose_name_plural = "주문 상세 항목 목록"

    def __str__(self):
        return f"{self.name} x {self.quantity}"


    