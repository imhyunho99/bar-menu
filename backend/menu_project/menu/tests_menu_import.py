"""
메뉴판 확인 화면 ↔ 저장 뷰의 계약.

확인 화면이 만들어내는 폼 필드 이름과 저장 뷰가 읽는 이름이 실제로 맞물리는지
본다. 여기가 어긋나면 조용히 0건 저장된다.

2026-08 부터 자동 인식을 끄고 사진을 사람에게 넘기므로(tests_menu_photo_relay),
업로드 화면에서 이 확인 화면으로 가는 길은 지금 닫혀 있다. 하지만 템플릿과
import_menu_commit 은 자동 인식을 다시 켤 때 그대로 쓸 것이라, 계약은 계속
고정해 둔다. 그래서 뷰를 거치지 않고 확인 화면을 직접 그린다.
"""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from .menu_import import MenuImportError, ParsedCategory, ParsedItem, ParsedMenu
from .models import Category, MenuItem, Restaurant

SAMPLE = ParsedMenu(
    categories=[
        ParsedCategory(
            name="사시미",
            name_en="SASHIMI",
            items=[
                ParsedItem(name="모둠 사시미", name_en="Assorted Sashimi", price="38,000",
                           description="당일 입고 선어 5종"),
                ParsedItem(name="연어 사시미", name_en="Salmon", price="26,000",
                           description="", confident=False),
            ],
        ),
        ParsedCategory(
            name="구이",
            items=[ParsedItem(name="닭꼬치 3종", price="16,000")],
        ),
    ],
    notes="우측 하단이 접혀 일부 가격을 읽지 못했습니다.",
)

# 업로드 파일 자리를 채우기만 하면 되는 최소 바이트 (stub 이 읽지 않는다)
DUMMY_IMAGE = b"not-a-real-image"


class MenuImportFlowTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.user = User.objects.create_user("owner", password="pw", is_staff=True, is_superuser=True)
        self.client.force_login(self.user)
        self.preview_url = f"/{self.restaurant.slug}/admin/menu/import/"
        self.commit_url = f"/{self.restaurant.slug}/admin/menu/import/commit/"

    def _preview_html(self):
        """자동 인식이 SAMPLE 을 돌려줬을 때 사장님이 보게 될 확인 화면."""
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        request = RequestFactory().get(self.preview_url)
        request.restaurant = self.restaurant
        request.user = self.user
        return render_to_string('admin/menu_import_preview.html', {
            'parsed': SAMPLE,
            'existing_categories': Category.objects.filter(
                restaurant=self.restaurant).order_by('priority', 'name'),
        }, request=request)

    def test_preview_renders_every_item_with_matching_field_names(self):
        html = self._preview_html()

        # 키가 빈 문자열로 무너지면 name="_name" 같은 필드가 나온다
        self.assertNotIn('name="_name"', html)
        for key in ("c0_i0", "c0_i1", "c1_i0"):
            self.assertIn(f'value="{key}"', html, f"{key} 체크박스가 없다")
            self.assertIn(f'name="{key}_price"', html, f"{key} 가격 필드가 없다")

        self.assertIn("우측 하단이 접혀", html)
        # 자신 없는 항목은 눈에 띄게 표시된다
        self.assertEqual(html.count("import-row unsure"), 1)

    def test_preview_form_posts_back_without_hand_written_field_names(self):
        """
        확인 화면이 실제로 뱉은 필드 이름만으로 저장까지 간다.

        다른 저장 테스트들은 POST 키를 손으로 적어서, 템플릿이 이름을 바꿔도
        초록불이 유지된다. 여기서는 HTML 을 파싱해 나온 이름만 되돌려 보내
        템플릿↔뷰 계약을 실제로 고정한다.
        """
        import re

        html = self._preview_html()

        # <form action=".../commit/"> 안의 input 만 긁는다
        form = html.split('import_menu_commit')[1] if 'import_menu_commit' in html else html
        form = html[html.index('<form'):html.index('</form>')]

        payload = {}
        for name, value in re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', form):
            payload.setdefault(name, []).append(value) if name == 'include' else payload.update({name: value})
        # 체크박스는 여러 개라 리스트로 유지
        payload['include'] = re.findall(r'name="include" value="([^"]+)"', form)
        payload.update({
            name: value
            for name, value in re.findall(r'<input type="text" name="([^"]+)" value="([^"]*)"', form)
        })
        payload.pop('csrfmiddlewaretoken', None)

        self.assertGreaterEqual(len(payload['include']), 3, '확인 화면에 항목이 안 나왔다')

        self.client.post(self.commit_url, payload)

        self.assertEqual(MenuItem.objects.filter(restaurant=self.restaurant).count(), 3)
        self.assertEqual(MenuItem.objects.get(name="모둠 사시미").price, "38,000")

    def test_commit_creates_categories_and_items(self):

        response = self.client.post(self.commit_url, {
            "include": ["c0_i0", "c0_i1", "c1_i0"],
            "c0_name": "사시미", "c0_name_en": "SASHIMI", "c0_existing": "",
            "c0_i0_name": "모둠 사시미", "c0_i0_name_en": "Assorted Sashimi",
            "c0_i0_price": "38,000", "c0_i0_description": "당일 입고 선어 5종",
            "c0_i1_name": "연어 사시미", "c0_i1_name_en": "Salmon",
            "c0_i1_price": "26,000", "c0_i1_description": "",
            "c1_name": "구이", "c1_name_en": "", "c1_existing": "",
            "c1_i0_name": "닭꼬치 3종", "c1_i0_name_en": "",
            "c1_i0_price": "16,000", "c1_i0_description": "",
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Category.objects.filter(restaurant=self.restaurant).count(), 2)
        self.assertEqual(MenuItem.objects.filter(restaurant=self.restaurant).count(), 3)

        item = MenuItem.objects.get(name="모둠 사시미")
        self.assertEqual(item.price, "38,000")
        self.assertEqual(item.category.name, "사시미")
        self.assertEqual(item.restaurant, self.restaurant)

    def test_unchecked_items_are_not_saved(self):

        self.client.post(self.commit_url, {
            "include": ["c0_i0"],  # 나머지는 체크 해제
            "c0_name": "사시미", "c0_existing": "",
            "c0_i0_name": "모둠 사시미", "c0_i0_price": "38,000",
            "c0_i1_name": "연어 사시미", "c0_i1_price": "26,000",
            "c1_name": "구이", "c1_existing": "",
            "c1_i0_name": "닭꼬치 3종", "c1_i0_price": "16,000",
        })

        self.assertEqual(MenuItem.objects.filter(restaurant=self.restaurant).count(), 1)
        # 항목이 하나도 안 들어간 카테고리는 만들지 않는다
        self.assertEqual(Category.objects.filter(restaurant=self.restaurant).count(), 1)

    def test_commit_can_target_an_existing_category(self):
        existing = Category.objects.create(name="기존 안주", restaurant=self.restaurant)

        self.client.post(self.commit_url, {
            "include": ["c0_i0"],
            "c0_name": "사시미", "c0_existing": str(existing.id),
            "c0_i0_name": "모둠 사시미", "c0_i0_price": "38,000",
        })

        self.assertEqual(Category.objects.filter(restaurant=self.restaurant).count(), 1)
        self.assertEqual(MenuItem.objects.get(name="모둠 사시미").category, existing)

    def test_unknown_category_id_is_rejected_not_orphaned(self):
        """
        남의 매장 카테고리 id (또는 그새 지워진 id) 를 보내면 저장을 막는다.
        그냥 두면 카테고리 없는 메뉴가 생기는데, 그건 손님 화면 어디에도
        뜨지 않으면서 어드민에는 등록된 것처럼 보인다.
        """
        other = Restaurant.objects.create(name="남의 매장", slug="rival")
        foreign = Category.objects.create(name="남의 카테고리", restaurant=other)

        self.client.post(self.commit_url, {
            "include": ["c0_i0"],
            "c0_name": "사시미", "c0_existing": str(foreign.id),
            "c0_i0_name": "모둠 사시미", "c0_i0_price": "38,000",
        })

        self.assertEqual(MenuItem.objects.filter(restaurant=self.restaurant).count(), 0)
        self.assertFalse(MenuItem.objects.filter(category__isnull=True).exists())

    def test_extractor_failure_is_shown_not_raised(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        with patch("menu.admin_views.parse_menu_image",
                   side_effect=MenuImportError("이미지 파일을 열 수 없습니다.")):
            response = self.client.post(
                self.preview_url,
                {"menu_image": SimpleUploadedFile("menu.jpg", DUMMY_IMAGE, content_type="image/jpeg")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("이미지 파일을 열 수 없습니다.", response.content.decode())
        self.assertEqual(MenuItem.objects.count(), 0)
