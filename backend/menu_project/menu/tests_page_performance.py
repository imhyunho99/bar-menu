"""
손님 화면의 렌더링 성능.

2026-05-01 측정에서 CLS 0.777, 총 3.4MB, HTTP/1.1 이 나왔다. 사장님이
"렌더링이 뚝뚝 끊긴다" 고 한 그 수치다. 여기서 고정하는 건 그때 찾은
병목들이 되돌아오지 않게 하는 계약이다.

성능은 눈에 안 보이는 채로 나빠진다 — 템플릿 한 줄, 아이콘 한 장을 바꿔도
아무도 즉시 알아채지 못하고, 다음 측정까지 몇 달이 간다. 그래서 수치가
아니라 원인을 테스트한다.
"""

import os
import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from PIL import Image

TEMPLATES = Path(__file__).resolve().parent / 'templates' / 'menu'
STATIC = Path(__file__).resolve().parents[1] / 'static'


class LcpImageIsNotLazyTests(TestCase):
    """
    첫 화면을 채우는 이미지에 loading="lazy" 를 붙이면 안 된다.

    lazy 는 '화면에 들어올 때 받는다' 는 뜻인데, LCP 요소는 이미 화면 안에
    있다. 브라우저는 레이아웃을 마친 뒤에야 그걸 알고 그때부터 받기 시작한다.
    2.2MB 짜리 인트로 이미지에서 이 지연이 LCP 를 200~400ms 늦췄다.
    """

    def test_intro_image_is_eager_and_prioritised(self):
        html = (TEMPLATES / 'menu_main.html').read_text(encoding='utf-8')
        intro = re.search(r'<img[^>]*class="intro-image"[^>]*>', html, re.S)
        self.assertIsNotNone(intro, 'intro-image 를 찾지 못했다')
        tag = intro.group(0)
        self.assertNotIn('loading="lazy"', tag, 'LCP 이미지가 lazy 다')
        self.assertIn('fetchpriority="high"', tag, 'LCP 이미지에 우선순위가 없다')


class StaticIconsAreNotOversizedTests(TestCase):
    """
    아이콘을 표시 크기의 몇 배로 내려받으면 대역폭과 디코딩이 그만큼 낭비된다.

    search.png·menu.png 는 456x192 인데 60x60 박스에 그려졌다. 넓이로 7.6배다.
    2x 화면까지 감안해도 긴 변 120px 이면 충분하다.
    """

    # 파일 → CSS 가 그리는 박스의 긴 변(px)
    RENDERED = {
        'search.png': 60,
        'menu.png': 60,
        'up.png': 60,
        'left.png': 60,
        'right.png': 60,
    }
    MAX_DPR = 2

    def test_icons_are_at_most_twice_the_rendered_size(self):
        for name, box in self.RENDERED.items():
            path = STATIC / name
            if not path.exists():
                continue
            with self.subTest(icon=name):
                with Image.open(path) as im:
                    self.assertLessEqual(
                        max(im.size), box * self.MAX_DPR,
                        f'{name} 이 {im.width}x{im.height} 다. {box}px 박스에는 '
                        f'긴 변 {box * self.MAX_DPR}px 이면 충분하다')


class UploadedImagesBecomeWebpTests(TestCase):
    """
    올라온 사진은 WebP 로 떨어져야 한다.

    실측: 프로젝트의 실제 이미지 9장이 PNG 15.7MB → JPEG 3.8MB → WebP 2.3MB.
    WebP 가 JPEG 보다 38% 더 작다. 인코딩이 10배 느리지만(12ms → 125ms)
    업로드 때 한 번뿐이라 값이 싸다.
    """

    def test_optimize_image_returns_webp(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile

        from .utils import optimize_image

        buf = io.BytesIO()
        Image.new('RGB', (2000, 1500), (200, 180, 160)).save(buf, 'PNG')
        upload = SimpleUploadedFile('menu.png', buf.getvalue(), content_type='image/png')

        result = optimize_image(upload, max_width=1200, quality=85)

        self.assertTrue(result.name.endswith('.webp'), f'{result.name} 이 webp 가 아니다')
        result.seek(0)
        with Image.open(result) as im:
            self.assertEqual(im.format, 'WEBP')
            self.assertLessEqual(im.width, 1200, '리사이즈가 안 됐다')


class ImagesCarryTheirDimensionsTests(TestCase):
    """
    <img> 에 width/height 가 없으면 브라우저는 이미지가 도착할 때까지 높이를
    모른다. 그동안 0 으로 잡아 두었다가 도착하는 순간 아래 내용을 밀어낸다.
    2026-05-01 측정의 CLS 0.777 이 그것이다 — 손님 눈에는 '페이지가 뚝뚝
    끊긴다' 로 보인다.

    CSS aspect-ratio 만으로는 부족했다. 그 값도 결국 우리가 아는 비율이어야
    하는데 사진마다 다르기 때문이다. 그래서 올릴 때 크기를 재서 저장하고
    템플릿이 그대로 내보낸다.
    """

    def _settings(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile

        from .models import Restaurant

        restaurant = Restaurant.objects.create(name='달빛', slug='moonlight')
        site = restaurant.site_settings.first()
        buf = io.BytesIO()
        Image.new('RGB', (1600, 2400), (200, 180, 160)).save(buf, 'PNG')
        site.intro_image = SimpleUploadedFile('intro.png', buf.getvalue(), content_type='image/png')
        site.save()
        site.refresh_from_db()
        return site

    def test_intro_image_records_its_size_after_upload(self):
        site = self._settings()
        self.assertTrue(site.intro_image_width, 'width 가 비어 있다')
        self.assertTrue(site.intro_image_height, 'height 가 비어 있다')
        # optimize_image 가 1200px 로 줄이므로 그 뒤의 크기여야 한다.
        # 원본 크기를 저장하면 브라우저가 예약한 높이와 실제가 어긋나 CLS 가 남는다.
        self.assertEqual(site.intro_image_width, 1200)
        self.assertEqual(site.intro_image_height, 1800)

    def test_template_emits_the_recorded_size(self):
        html = (TEMPLATES / 'menu_main.html').read_text(encoding='utf-8')
        intro = re.search(r'<img[^>]*class="intro-image"[^>]*>', html, re.S).group(0)
        self.assertIn('site_settings.intro_image_width', intro)
        self.assertIn('site_settings.intro_image_height', intro)


class BackfillLegacyImagesTests(TestCase):
    """
    이미 올라와 있는 PNG 들.

    optimize_image 가 WebP 로 떨어뜨리게 된 건 나중이라, 그 전에 올라온 파일은
    아직 PNG 다. 실측으로 프로젝트 미디어 15.7MB 중 대부분이 여기 해당한다 —
    WebP 로 옮기면 2.3MB 다. width/height 도 그때 함께 채운다.
    """

    def _site_with_png(self):
        import io

        from django.core.files.base import ContentFile

        from .models import Restaurant

        restaurant = Restaurant.objects.create(name='달빛', slug='moonlight')
        site = restaurant.site_settings.first()
        buf = io.BytesIO()
        Image.new('RGB', (1600, 2400), (190, 170, 150)).save(buf, 'PNG')
        # optimize_image 를 건너뛰고 PNG 그대로 넣는다 — 옛 데이터와 같은 상태
        site.intro_image.save('legacy.png', ContentFile(buf.getvalue()), save=False)
        type(site).objects.filter(pk=site.pk).update(
            intro_image=site.intro_image.name, intro_image_width=None, intro_image_height=None)
        site.refresh_from_db()
        return site

    def _run(self, **opts):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('convert_images_to_webp', stdout=out, **opts)
        return out.getvalue()

    def test_legacy_png_becomes_webp_with_dimensions(self):
        site = self._site_with_png()
        self.assertTrue(site.intro_image.name.endswith('.png'))
        # 옛 행은 백필 전까지 크기가 비어 있다. 파일을 읽어 채우지 않는 게
        # 의도다 — 채우려면 행마다 파일을 열어야 하고, 그게 CLS 를 고치려다
        # 페이지를 느리게 만드는 함정이다(DimensionsDoNotCostFileReadsTests).
        self.assertIsNone(site.intro_image_width)

        self._run()

        site.refresh_from_db()
        self.assertTrue(site.intro_image.name.endswith('.webp'), site.intro_image.name)
        self.assertEqual(site.intro_image_width, 1200)
        self.assertEqual(site.intro_image_height, 1800)

    def test_dry_run_changes_nothing(self):
        site = self._site_with_png()
        output = self._run(dry_run=True)
        site.refresh_from_db()
        self.assertTrue(site.intro_image.name.endswith('.png'))
        self.assertIn('legacy', output)

    def test_already_webp_is_left_alone(self):
        """
        다시 인코딩하면 화질만 깎인다. 명령을 두 번 돌려도 안전해야 한다 —
        운영에서 한 번 돌리고 결과가 미심쩍어 또 돌리는 일은 늘 생긴다.
        """
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile

        from .models import Restaurant

        restaurant = Restaurant.objects.create(name='별빛', slug='starlight')
        site = restaurant.site_settings.first()
        buf = io.BytesIO()
        Image.new('RGB', (900, 600), (120, 140, 160)).save(buf, 'PNG')
        site.intro_image = SimpleUploadedFile('a.png', buf.getvalue(), content_type='image/png')
        site.save()                                   # 여기서 이미 webp 가 된다
        site.refresh_from_db()
        before = (site.intro_image.name, site.intro_image.size)

        self._run()

        site.refresh_from_db()
        self.assertEqual((site.intro_image.name, site.intro_image.size), before)


class DimensionsDoNotCostFileReadsTests(TestCase):
    """
    크기를 저장하는 방식이 페이지를 느리게 만들면 안 된다.

    Django 의 width_field/height_field 를 쓰면 값이 비어 있는 동안 **객체를
    읽을 때마다 파일을 연다**(post_init 의 update_dimension_fields). 메뉴 50개
    페이지면 요청당 50번이고, 파일이 사라진 행이 하나라도 있으면 목록 전체가
    FileNotFoundError 로 터진다. 실제로 로컬 미디어에서 그 크래시를 봤다.

    그래서 크기는 저장할 때 한 번 계산해 넣고, 읽을 때는 컬럼만 본다.
    """

    def _menu_item_with_image(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile

        from .models import Category, MenuItem, Restaurant

        restaurant = Restaurant.objects.create(name='달빛', slug='moonlight')
        category = Category.objects.create(name='사시미', restaurant=restaurant)
        buf = io.BytesIO()
        Image.new('RGB', (1600, 1200), (170, 160, 150)).save(buf, 'PNG')
        return MenuItem.objects.create(
            name='모둠 사시미', price='38,000', category=category, restaurant=restaurant,
            menu_image=SimpleUploadedFile('m.png', buf.getvalue(), content_type='image/png'),
        )

    def test_reading_rows_never_opens_the_image_file(self):
        from unittest import mock

        from .models import MenuItem

        item = self._menu_item_with_image()
        self.assertTrue(item.menu_image_width, '저장 시점에 크기가 안 들어갔다')

        # DefaultStorage 는 프록시라 실제 구현 클래스를 잡아야 한다
        from django.core.files.storage import FileSystemStorage

        opened = []
        original = FileSystemStorage._open

        def spy(self, name, mode='rb'):
            opened.append(name)
            return original(self, name, mode)

        with mock.patch.object(FileSystemStorage, '_open', spy):
            for row in MenuItem.objects.all():
                _ = (row.menu_image_width, row.menu_image_height, row.name)

        self.assertEqual(opened, [], f'목록을 읽는데 파일을 {len(opened)}번 열었다')

    def test_a_missing_file_does_not_break_the_list(self):
        """
        파일이 사라진 행은 실제로 있다(로컬 미디어에서 확인). 그 한 줄 때문에
        손님 메뉴판 전체가 500 이 되면 안 된다.
        """
        import os

        from .models import MenuItem

        item = self._menu_item_with_image()
        os.remove(item.menu_image.path)

        rows = list(MenuItem.objects.all())          # 여기서 터지면 안 된다
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].menu_image_width, 800)   # 저장해 둔 값은 남아 있다

    def test_rows_with_no_recorded_size_still_do_not_open_files(self):
        """
        마이그레이션 직후의 상태다. 모든 행의 width/height 가 NULL 이고, 그때
        Django 의 width_field/height_field 는 **행을 읽을 때마다 파일을 연다**.
        손님 메뉴판 한 번에 50번이고, 사라진 파일이 하나라도 있으면 목록 전체가
        FileNotFoundError 로 죽는다. 배포 직후 백필을 돌리기 전까지가 그 구간이다.

        그 구간이 존재하지 않아야 한다.
        """
        import os
        from unittest import mock

        from django.core.files.storage import FileSystemStorage

        from .models import MenuItem

        item = self._menu_item_with_image()
        # 마이그레이션 직후와 같은 상태로 되돌린다
        MenuItem.objects.filter(pk=item.pk).update(menu_image_width=None, menu_image_height=None)

        opened = []
        original = FileSystemStorage._open

        def spy(self, name, mode='rb'):
            opened.append(name)
            return original(self, name, mode)

        with mock.patch.object(FileSystemStorage, '_open', spy):
            list(MenuItem.objects.all())

        self.assertEqual(opened, [],
                         f'크기가 비어 있다고 파일을 {len(opened)}번 열었다')

        # 그리고 파일이 없어도 죽지 않아야 한다
        os.remove(item.menu_image.path)
        MenuItem.objects.filter(pk=item.pk).update(menu_image_width=None, menu_image_height=None)
        self.assertEqual(len(list(MenuItem.objects.all())), 1)


class DimensionBackfillTests(TestCase):
    """
    이미 WebP 인 이미지도 크기는 비어 있다.

    운영을 확인해 보니 이미지가 전부 WebP 였다(2026-08-23). 그래서 포맷 변환은
    할 일이 없는데, CLS 를 위한 width/height 는 여전히 비어 있다. 포맷 변환과
    크기 채우기는 다른 일이므로 따로 처리해야 한다 — 이미 WebP 인 파일을 다시
    인코딩하면 화질만 깎인다.
    """

    def _webp_item(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile

        from .models import Category, MenuItem, Restaurant

        restaurant = Restaurant.objects.create(name='달빛', slug='moonlight')
        category = Category.objects.create(name='사시미', restaurant=restaurant)
        buf = io.BytesIO()
        Image.new('RGB', (1200, 900), (180, 170, 160)).save(buf, 'PNG')
        item = MenuItem.objects.create(
            name='모둠', price='38,000', category=category, restaurant=restaurant,
            menu_image=SimpleUploadedFile('m.png', buf.getvalue(), content_type='image/png'))
        # 옛 데이터처럼 크기만 비운다 (파일은 이미 webp)
        MenuItem.objects.filter(pk=item.pk).update(menu_image_width=None, menu_image_height=None)
        item.refresh_from_db()
        return item

    def test_backfill_fills_dimensions_without_reencoding(self):
        from io import StringIO

        from django.core.management import call_command

        from .models import MenuItem

        item = self._webp_item()
        self.assertTrue(item.menu_image.name.endswith('.webp'))
        self.assertIsNone(item.menu_image_width)
        before = (item.menu_image.name, item.menu_image.size)

        call_command('convert_images_to_webp', stdout=StringIO())

        item.refresh_from_db()
        self.assertEqual(item.menu_image_width, 800)     # optimize_image 가 800 으로 줄였다
        self.assertEqual(item.menu_image_height, 600)
        # 파일은 손대지 않았다 — 다시 인코딩하면 화질만 깎인다
        self.assertEqual((item.menu_image.name, item.menu_image.size), before)


class TemplateNeverEmitsNoneTests(TestCase):
    """
    크기를 모르는 이미지에 width="None" 을 뱉으면 안 된다.

    Django 템플릿은 None 을 문자열 "None" 으로 그린다. 브라우저는 그 속성을
    무시하지만 HTML 이 깨지고, 무엇보다 백필 전 상태가 그대로 배포된다.
    모를 때는 속성을 아예 내보내지 않는 게 맞다.
    """

    def test_templates_guard_the_dimension_attributes(self):
        for name in ('menu_main.html', 'menu_list.html', 'category_list.html'):
            html = (TEMPLATES / name).read_text(encoding='utf-8')
            for match in re.finditer(r'(width|height)="\{\{ ([^}]+) \}\}"', html):
                with self.subTest(template=name, expr=match.group(2)):
                    self.assertIn(
                        'default_if_none', match.group(2),
                        f'{name}: {match.group(0)} 이 None 이면 width="None" 이 나간다')
