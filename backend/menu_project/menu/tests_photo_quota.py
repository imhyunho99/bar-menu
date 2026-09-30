"""
사진 메뉴등록은 공개 전 매장에 1회.

이 기능의 실체는 비전 API 가 아니라 사람의 손이다. 사진이 Discord 로 오면
우리가 보고 타이핑해 넣는다. 그래서 무제한으로 열어 둘 수 없다.
"""

from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from menu.models import Restaurant, UserProfile


def _one_photo():
    buffer = BytesIO()
    Image.new('RGB', (40, 40), 'white').save(buffer, format='JPEG')
    return SimpleUploadedFile('menu.jpg', buffer.getvalue(), content_type='image/jpeg')


class PhotoImportQuotaTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)
        self.client.force_login(self.user)

    def _send(self):
        return self.client.post(
            '/unpaid-bar/admin/menu/import/', {'menu_image': _one_photo()}, follow=True,
        )

    def _subscription(self):
        return Restaurant.objects.get(slug='unpaid-bar').subscription

    def test_a_free_store_gets_one_send(self):
        with patch('menu.notifications.send_menu_photos', return_value=True):
            self._send()

        self.assertEqual(self._subscription().photo_import_count, 1)

    def test_a_second_send_is_refused_for_a_free_store(self):
        subscription = self.restaurant.subscription
        subscription.photo_import_count = 1
        subscription.save(update_fields=['photo_import_count'])

        with patch('menu.notifications.send_menu_photos', return_value=True) as send:
            response = self._send()

        send.assert_not_called()
        self.assertContains(response, '직접 입력은 계속 무료')

    def test_a_paid_store_is_not_counted(self):
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.photo_import_count = 5
        subscription.save(update_fields=['status', 'photo_import_count'])

        with patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self._send()

        send.assert_called_once()

    def test_a_failed_send_does_not_spend_the_free_turn(self):
        """사진이 못 갔는데 횟수만 줄면 사장님은 한 번도 못 써 보고 끝난다."""
        with patch('menu.notifications.send_menu_photos', return_value=False):
            self._send()

        self.assertEqual(self._subscription().photo_import_count, 0)

    def test_the_owner_is_told_the_preview_will_be_empty_for_a_while(self):
        """
        사진을 보낸 사장님은 우리가 손을 댈 때까지 미리보기가 비어 있다.
        말하지 않으면 빈 메뉴판을 보고 고장인 줄 안다.
        """
        with patch('menu.notifications.send_menu_photos', return_value=True):
            response = self._send()

        self.assertContains(response, '정리하는 중')

    def _photo_alert_title(self, restaurant):
        from menu.notifications import build_menu_photo_payload

        # 제목만 본다. 페이로드 전체를 문자열로 훑으면 매장 이름에 '미결제'
        # 가 들어간 가게에서 엉뚱하게 매칭된다.
        return build_menu_photo_payload(restaurant, count=3)['embeds'][0]['title']

    def test_the_alert_says_the_store_has_not_paid(self):
        """이 사진을 정리하는 데 드는 건 우리 시간이다. 우선순위를 고를 근거."""
        self.assertIn('미결제', self._photo_alert_title(self.restaurant))

    def test_the_alert_does_not_nag_about_a_paying_store(self):
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.save(update_fields=['status'])

        title = self._photo_alert_title(Restaurant.objects.get(slug='unpaid-bar'))
        self.assertNotIn('미결제', title)
