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
        verbose_name="인트로 비디오",
        help_text="로딩 화면에 표시될 인트로 비디오 (MP4 파일)"
    )
    side_image = models.ImageField(
        upload_to='site_images/',
        blank=True,
        null=True,
        verbose_name="사이드 이미지",
        help_text="사이드 메뉴 등에 사용될 이미지"
    )
    background_color = models.CharField(
        max_length=20, 
        default='#000000', 
        verbose_name="배경색", 
        help_text="사이트 배경색 (예: #000000)"
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
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items', null=True, blank=True)
    # 1. 이름
    name = models.CharField(max_length=100, verbose_name="메뉴명")
    
    # 2. 영문명
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name="메뉴명(영문)")

    # 3. 가격
    price = models.TextField(verbose_name="가격", help_text="가격을 입력하세요 (예: 15000, 15.5, 15,000)")

    # 3. 설명
    description = models.TextField(verbose_name="메뉴 설명")

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
        super().save(*args, **kwargs)
    