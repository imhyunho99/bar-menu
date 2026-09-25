"""
업로드가 관리자 원점에 스크립트를 심을 수 있는가.

미디어는 관리자(`api.*`)와 **같은 원점**에서 서빙된다. 폰트 자리에 .html 을
올릴 수 있으면 그 원점에서 스크립트가 돌고, 지원하러 남의 매장 설정을 열어
본 슈퍼유저의 세션에서 실행된다. 무료 가입 한 번으로 관리자가 넘어간다.

2026-09-25 적대적 검토에서 실제로 뚫렸다 — dev 관리자 폼으로 그냥 올라갔고
/media/fonts/<x>.html 이 content-type: text/html 로 내려왔다.

nosniff 로는 못 막는다. 선언된 타입이 진짜 text/html 이라 스니핑 문제가
아니다. 받지 않는 것이 유일한 방법이라, 여기서 '안 받는가' 를 본다.
"""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from menu.models import Restaurant, SiteSettings, UserProfile

PAYLOAD = b"<!doctype html><script>alert(1)</script>"

FONT_FIELDS = [
    'menu_name_font', 'menu_name_en_font', 'menu_price_font',
    'menu_description_font', 'menu_notes_font', 'category_name_font',
    'category_name_en_font', 'pairing_name_font', 'pairing_description_font',
    'pairing_price_font',
]
VIDEO_FIELDS = ['intro_video', 'loading_video_2']


class UploadsCannotCarryScriptTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛', slug='moonlight')
        self.settings = SiteSettings.objects.create(restaurant=self.restaurant)

    def _reject(self, field, filename, content=PAYLOAD):
        setattr(self.settings, field, SimpleUploadedFile(filename, content))
        with self.assertRaises(ValidationError, msg=f'{field} 가 {filename} 을 받았습니다'):
            self.settings.full_clean(exclude=[
                f.name for f in SiteSettings._meta.get_fields()
                if getattr(f, 'name', None) not in (field,)
            ])

    def test_no_font_field_accepts_html(self):
        for field in FONT_FIELDS:
            with self.subTest(field=field):
                self._reject(field, 'payload.html')

    def test_no_font_field_accepts_svg(self):
        """SVG 는 이미지처럼 보이지만 스크립트를 담는다."""
        for field in FONT_FIELDS:
            with self.subTest(field=field):
                self._reject(field, 'payload.svg', b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>')

    def test_video_fields_do_not_accept_html(self):
        for field in VIDEO_FIELDS:
            with self.subTest(field=field):
                self._reject(field, 'payload.html')

    def test_real_fonts_still_go_through(self):
        """막는 것이 목적이지, 폰트를 못 쓰게 하는 것이 아니다."""
        for field in FONT_FIELDS:
            with self.subTest(field=field):
                setattr(self.settings, field, SimpleUploadedFile('brand.woff2', b'\x77\x4fF2 fake'))
                self.settings.full_clean(exclude=[
                    f.name for f in SiteSettings._meta.get_fields()
                    if getattr(f, 'name', None) not in (field,)
                ])

    def test_every_file_field_has_an_allowlist(self):
        """
        필드가 나중에 늘어날 때가 위험하다. 하나라도 빠지면 같은 구멍이
        그대로 다시 생긴다.
        """
        missing = []
        for field in SiteSettings._meta.get_fields():
            if field.__class__.__name__ != 'FileField':
                continue
            allowed = [e for v in field.validators for e in getattr(v, 'allowed_extensions', [])]
            if not allowed:
                missing.append(field.name)
        self.assertEqual(missing, [], f'확장자 허용목록이 없는 FileField: {missing}')


class TheAdminFormRefusesIt(TestCase):
    """모델 검증만으로는 부족하다. 사장님이 실제로 지나가는 길로 확인한다."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛', slug='moonlight')
        self.settings = SiteSettings.objects.create(restaurant=self.restaurant)
        self.user = User.objects.create_superuser('boss', 'b@x.test', 'pw-7731')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)
        self.client.force_login(self.user)

    def test_posting_html_to_the_font_field_is_rejected(self):
        response = self.client.post(
            f'/admin/menu/sitesettings/{self.settings.pk}/change/',
            {
                'restaurant': self.restaurant.pk,
                'menu_name_font': SimpleUploadedFile('payload.html', PAYLOAD),
            },
        )
        # 폼이 다시 그려진다(302 면 저장된 것이다).
        self.assertEqual(response.status_code, 200)
        self.settings.refresh_from_db()
        self.assertFalse(self.settings.menu_name_font, '저장됐습니다')
