"""
메뉴판 사진을 우리에게 넘긴다.

비전 호출은 하지 않는다. 사장님이 올린 사진을 Discord 로 그대로 보내고,
우리가 손으로 정리해 넣어 준다. 그래서 이 경로에서 가장 중요한 성질은
'사진이 실제로 우리에게 도착했는가' 이고, 두 번째가 '도착하지 않았는데
도착했다고 말하지 않는가' 이다. 후자가 깨지면 사장님은 기다리고 우리는
모른다 — 아무도 눈치채지 못한 채 며칠이 간다.
"""

import io
import json
import os
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from . import notifications
from .models import Restaurant, UserProfile
from .menu_import import MAX_IMAGES


def photo(name='menu.jpg', size=(1200, 900), color=(200, 180, 160)):
    buf = io.BytesIO()
    Image.new('RGB', size, color).save(buf, 'JPEG', quality=85)
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/jpeg')


class MenuPhotoRelayTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛 이자카야', slug='moonlight')
        owner = User.objects.create_user('owner@example.com', email='owner@example.com',
                                         password='pw', is_staff=True)
        UserProfile.objects.create(user=owner, restaurant=self.restaurant, phone='050-1234-5678')
        self.client.force_login(owner)
        self.url = '/moonlight/admin/menu/import/'

    def _post(self, n=1, **kwargs):
        return self.client.post(self.url, {'menu_image': [photo(f'p{i}.jpg') for i in range(n)]},
                                follow=True, **kwargs)

    # ── 비전 API 는 부르지 않는다 ────────────────────────────────
    def test_vision_api_is_never_called(self):
        """
        이 경로의 존재 이유다. 한 번이라도 불리면 키가 없는 지금은 에러가,
        키를 넣은 뒤에는 청구서가 나온다.
        """
        with mock.patch('menu.menu_import.parse_menu_image') as vision:
            with mock.patch('menu.notifications.send_menu_photos', return_value=True):
                self._post(1)
        vision.assert_not_called()

    # ── 사진이 우리에게 간다 ─────────────────────────────────────
    def test_photos_are_sent_to_us(self):
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self._post(3)
        send.assert_called_once()
        restaurant, images = send.call_args[0][0], send.call_args[0][1]
        self.assertEqual(restaurant.slug, 'moonlight')
        self.assertEqual(len(images), 3)

    def test_owner_is_told_we_will_handle_it(self):
        with mock.patch('menu.notifications.send_menu_photos', return_value=True):
            response = self._post(1)
        self.assertContains(response, '확인 후')

    # ── 도착하지 않았으면 도착했다고 하지 않는다 ─────────────────
    def test_failed_delivery_does_not_claim_success(self):
        """
        웹훅이 죽어 있으면 사진은 아무 데도 안 갔다. 그런데 '받았습니다' 가
        뜨면 사장님은 기다리고 우리는 모른다. 이 경로만 동기로 보내는 이유다.
        """
        with mock.patch('menu.notifications.send_menu_photos', return_value=False):
            response = self._post(1)
        self.assertNotContains(response, '확인 후')
        self.assertContains(response, '다시')

    # ── 장수 ─────────────────────────────────────────────────────
    def test_ten_photos_are_accepted(self):
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self._post(MAX_IMAGES)
        self.assertEqual(len(send.call_args[0][1]), MAX_IMAGES)

    def test_eleventh_photo_is_refused_with_a_countable_reason(self):
        """조용히 자르면 사장님은 안 올라간 페이지가 있는 줄 모른다."""
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            response = self._post(MAX_IMAGES + 1)
        send.assert_not_called()
        self.assertContains(response, f'{MAX_IMAGES}장')

    def test_no_photo_is_refused(self):
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            response = self.client.post(self.url, {}, follow=True)
        send.assert_not_called()
        self.assertContains(response, '선택해')

    # ── 사진은 줄여서 보낸다 ─────────────────────────────────────
    def test_photos_are_shrunk_before_leaving(self):
        """
        브라우저가 줄여 보내는 게 정상 경로지만, JS 가 꺼져 있거나 구형 폰이면
        원본이 그대로 온다. 그때 Discord 한도를 넘겨 전송이 통째로 실패하면
        사장님은 이유를 알 수 없다. 서버에서 한 번 더 줄인다.
        """
        big = photo('big.jpg', size=(4000, 3000))
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self.client.post(self.url, {'menu_image': [big]}, follow=True)
        sent = send.call_args[0][1][0]
        with Image.open(io.BytesIO(sent)) as im:
            self.assertLessEqual(max(im.size), 2000)


class DiscordMultipartTests(TestCase):
    """
    손으로 만든 multipart 본문.

    여기가 조금이라도 어긋나면 Discord 는 400 을 주고 사진은 영영 도착하지
    않는다. 라이브러리를 안 쓰는 대신(운영 인스턴스에 requests 를 더 얹지
    않으려고) 실제로 파싱해서 확인한다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛 이자카야', slug='moonlight')
        owner = User.objects.create_user('owner@example.com', email='owner@example.com', password='pw')
        UserProfile.objects.create(user=owner, restaurant=self.restaurant, phone='050-1234-5678')

    def _parse(self, body, content_type):
        """서버가 받는 것과 같은 방식으로 되돌려 읽는다."""
        from email import message_from_bytes

        msg = message_from_bytes(
            b'Content-Type: ' + content_type.encode() + b'\r\nMIME-Version: 1.0\r\n\r\n' + body
        )
        self.assertTrue(msg.is_multipart(), 'multipart 로 안 읽힌다')
        parts = {}
        for part in msg.get_payload():
            disposition = part.get('Content-Disposition', '')
            name = disposition.split('name="')[1].split('"')[0]
            parts[name] = part.get_payload(decode=True)
        return parts

    def test_body_is_well_formed_and_carries_every_photo(self):
        images = [b'\xff\xd8\xff-fake-jpeg-%d' % i for i in range(3)]
        payload = notifications.build_menu_photo_payload(self.restaurant, 3)
        body, content_type = notifications._multipart(payload, images, 0)

        parts = self._parse(body, content_type)
        self.assertIn('payload_json', parts)
        for i, image in enumerate(images):
            self.assertEqual(parts[f'files[{i}]'], image, f'{i}번째 사진이 깨졌다')

    def test_payload_json_carries_contact_details(self):
        payload = notifications.build_menu_photo_payload(self.restaurant, 1)
        body, content_type = notifications._multipart(payload, [b'x'], 0)
        sent = json.loads(self._parse(body, content_type)['payload_json'])
        text = str(sent)
        self.assertIn('달빛 이자카야', text)
        self.assertIn('/moonlight', text)
        self.assertIn('owner@example.com', text)
        self.assertIn('050-1234-5678', text)

    def test_boundary_never_appears_inside_the_photo_bytes(self):
        """
        경계가 사진 안에 들어 있으면 본문이 한가운데서 끊기고, 잘린 사진이
        도착한다. 눈에 안 보이는 종류의 실패라 못박는다.
        """
        images = [b'\x00' * 2048, b'\xff' * 2048]
        payload = notifications.build_menu_photo_payload(self.restaurant, 2)
        body, content_type = notifications._multipart(payload, images, 0)
        boundary = content_type.split('boundary=')[1].encode()

        for i, image in enumerate(images):
            self.assertNotIn(boundary, image, f'{i}번째 사진 안에 경계가 들어 있다')
        # 파트 3개(payload_json + 사진 2장) 앞에 하나씩, 그리고 종료 표시 하나.
        self.assertEqual(body.count(boundary), 4)
        # 그리고 실제로 되읽힌다 — 위 계산이 맞았다는 최종 확인.
        parts = self._parse(body, content_type)
        self.assertEqual(parts['files[1]'], images[1])

    def test_large_sets_are_split_across_messages_not_refused(self):
        """
        사장님은 몇 MB 인지 모른다. 한도를 넘었다고 거절하면 이유를 알 수 없다.
        나눠 보내는 건 우리 사정이므로 조용히 처리한다.
        """
        big = [b'x' * (3 * 1024 * 1024) for _ in range(4)]   # 12MB
        batches = notifications._batch(big)
        self.assertGreater(len(batches), 1, '나뉘지 않았다')
        self.assertEqual(sum(len(b) for b in batches), 4, '나누다가 사진을 잃었다')
        for group in batches:
            self.assertLessEqual(sum(len(i) for i in group), notifications._DISCORD_BATCH_BYTES)

    def test_a_single_oversized_photo_is_still_sent_alone(self):
        """혼자서 한도를 넘는 사진도 버리지 않는다. 버리면 아무도 모른다."""
        batches = notifications._batch([b'x' * (9 * 1024 * 1024)])
        self.assertEqual(len(batches), 1)

    def test_partial_failure_reports_failure(self):
        """앞 묶음만 도착했는데 True 를 주면 남은 장을 영영 못 본다."""
        images = [b'x' * (5 * 1024 * 1024), b'y' * (5 * 1024 * 1024)]
        calls = []

        def flaky(request, timeout=None):
            calls.append(request)
            if len(calls) == 2:
                raise OSError('두 번째 묶음 실패')
            return mock.MagicMock()

        with mock.patch.dict(os.environ, {'DISCORD_WEBHOOK_URL': 'https://discord.test/hook'}):
            with mock.patch('urllib.request.urlopen', side_effect=flaky):
                ok = notifications.send_menu_photos(self.restaurant, images)
        self.assertEqual(len(calls), 2)
        self.assertFalse(ok)

    def test_missing_webhook_reports_failure_rather_than_silence(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(notifications.send_menu_photos(self.restaurant, [b'x']))

    def test_wire_format_uses_crlf_everywhere(self):
        """
        multipart 는 줄 끝이 CRLF 여야 한다(RFC 2046).

        Python 의 email 파서는 LF 만 있어도 읽어 주므로, 파싱이 되는지만 보는
        테스트는 이 버그를 통과시킨다. 실제로 확인해 보니 CRLF 를 LF 로 바꿔도
        위 테스트들이 전부 초록불이었다. Discord 는 400 을 준다. 그래서 바이트를
        직접 본다.
        """
        payload = notifications.build_menu_photo_payload(self.restaurant, 1)
        body, content_type = notifications._multipart(payload, [b'\xff\xd8\xff-jpeg'], 0)
        boundary = content_type.split('boundary=')[1].encode()

        # 구조 부분(사진 바이트 제외)에 홀로 선 LF 가 있으면 안 된다
        structural = body.split(b'\xff\xd8\xff-jpeg')
        for chunk in structural:
            self.assertNotIn(b'\n', chunk.replace(b'\r\n', b''),
                             'CRLF 가 아닌 개행이 섞였다')

        self.assertTrue(body.startswith(b'--' + boundary + b'\r\n'))
        self.assertTrue(body.endswith(b'--' + boundary + b'--\r\n'))
        # 헤더와 본문 사이는 빈 줄 하나 — CRLFCRLF
        self.assertIn(b'Content-Type: image/jpeg\r\n\r\n', body)
        self.assertIn(b'Content-Type: application/json\r\n\r\n', body)
