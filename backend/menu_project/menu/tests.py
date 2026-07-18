import json
import os
from unittest import mock

from django.test import TestCase

from .models import ContactSubmission
from . import notifications


class ContactNotificationTest(TestCase):
    def setUp(self):
        self.submission = ContactSubmission.objects.create(
            name="테스트가게", contact_info="010-1234-5678", plan="premium"
        )

    def test_payload_includes_submission_fields(self):
        payload = notifications.build_contact_payload(self.submission)
        blob = json.dumps(payload, ensure_ascii=False)
        self.assertIn("테스트가게", blob)
        self.assertIn("010-1234-5678", blob)
        self.assertIn("premium", blob)

    def test_request_avoids_default_urllib_user_agent(self):
        # Discord/Cloudflare는 기본 "Python-urllib/x" UA를 403으로 막는다.
        payload = notifications.build_contact_payload(self.submission)
        request = notifications._build_request("https://discord.test/hook", payload)
        user_agent = request.get_header("User-agent")
        self.assertIsNotNone(user_agent)
        self.assertNotIn("urllib", user_agent.lower())

    def test_skips_when_webhook_url_unset(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("DISCORD_WEBHOOK_URL", None)
            with mock.patch.object(notifications, "_post") as posted:
                result = notifications.send_contact_notification(self.submission)
        self.assertIsNone(result)
        posted.assert_not_called()

    def test_posts_when_webhook_url_set(self):
        with mock.patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://discord.test/hook"}):
            with mock.patch.object(notifications, "_post") as posted:
                thread = notifications.send_contact_notification(self.submission)
                self.assertIsNotNone(thread)
                thread.join(timeout=3)
        posted.assert_called_once()

    def test_delivery_failure_is_swallowed(self):
        with mock.patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://discord.test/hook"}):
            with mock.patch.object(notifications, "_post", side_effect=RuntimeError("boom")):
                thread = notifications.send_contact_notification(self.submission)
                thread.join(timeout=3)
        # 예외가 여기까지 전파되지 않으면 통과 — 문의 저장·응답이 알림 실패에 영향받지 않는다.


class ContactViewNotificationTest(TestCase):
    def test_view_saves_and_triggers_notification(self):
        with mock.patch("menu.api.views.send_contact_notification") as notify:
            response = self.client.post(
                "/api/v1/contact/",
                data=json.dumps({"name": "뷰가게", "contact_info": "010-0000", "plan": "basic"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ContactSubmission.objects.filter(name="뷰가게").exists())
        notify.assert_called_once()

