"""
요금제 가격.

카카오페이 심사는 '상품명·판매가격·결제버튼 활성화'를 본다. 가격이 마케팅
페이지에만 있고 결제 화면에 없으면 심사에서 걸리고, 두 곳에 따로 적어 두면
언젠가 갈린다. 값은 백엔드에 하나만 두고 양쪽이 그걸 쓴다.
"""

import json
import re
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Restaurant, Subscription, UserProfile

# frontend/src/lib/marketing-content.ts
MARKETING_CONTENT = (
    Path(__file__).resolve().parents[3] / 'frontend' / 'src' / 'lib' / 'marketing-content.ts'
)


class PlanPriceTests(TestCase):
    def test_every_plan_has_a_price(self):
        for code, _label in Subscription.PLAN_CHOICES:
            with self.subTest(plan=code):
                self.assertIn(code, Subscription.PLAN_PRICES)
                self.assertGreater(Subscription.PLAN_PRICES[code], 0)

    def test_prices_match_the_marketing_page(self):
        """
        손님이 요금 페이지에서 본 금액과 결제 화면 금액이 다르면 그건 사고다.
        마케팅 페이지 쪽이 바뀌면 이 테스트가 먼저 깨진다.
        """
        source = MARKETING_CONTENT.read_text(encoding='utf-8')
        block = re.search(r'export const PLANS[^=]*=\s*\[(.*?)\n\];', source, re.S)
        self.assertIsNotNone(block, 'marketing-content.ts 에서 PLANS 를 찾지 못했습니다')

        found = dict(re.findall(r"id:\s*'([a-z]+)'.*?price:\s*'([\d,]+)'", block.group(1), re.S))
        self.assertTrue(found, 'PLANS 에서 id/price 를 읽지 못했습니다')

        for code, price_text in found.items():
            with self.subTest(plan=code):
                self.assertEqual(Subscription.PLAN_PRICES[code], int(price_text.replace(',', '')))

    def test_every_plan_is_under_the_review_ceiling(self):
        """카카오페이 심사: 500만원 이상 고액상품은 일부 카드사에서 심사 불가."""
        for code, price in Subscription.PLAN_PRICES.items():
            with self.subTest(plan=code):
                self.assertLess(price, 5_000_000)


class CheckoutScreenTests(TestCase):
    """심사자가 로그인해서 보는 결제 화면."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.owner = User.objects.create_user(username='owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant)
        self.client.force_login(self.owner)
        self.url = '/moonlight/admin/billing/'

    def test_checkout_shows_product_name_and_price(self):
        body = self.client.get(self.url).content.decode()
        for code, label in Subscription.PLAN_CHOICES:
            with self.subTest(plan=code):
                self.assertIn(label, body)
                self.assertIn(f'{Subscription.PLAN_PRICES[code]:,}', body)

    def test_checkout_states_the_recurring_terms(self):
        """정기결제 방식·결제 시기·취소·이의신청이 화면에 있어야 한다."""
        body = self.client.get(self.url).content.decode()
        for phrase in ('매월', '부가세', '해지', '이의신청'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_checkout_links_to_the_terms(self):
        self.assertIn('/terms', self.client.get(self.url).content.decode())


BUSINESS_TS = Path(__file__).resolve().parents[3] / 'frontend' / 'src' / 'lib' / 'business.ts'


def _business_field(label):
    """business.ts 의 BUSINESS 목록에서 한 항목의 값을 읽는다."""
    source = BUSINESS_TS.read_text(encoding='utf-8')
    block = re.search(r'export const BUSINESS[^=]*=\s*\[(.*?)\n\];', source, re.S)
    if block is None:
        raise AssertionError('business.ts 에서 BUSINESS 를 찾지 못했습니다')
    found = dict(re.findall(r"label:\s*'([^']*)',\s*value:\s*'([^']*)'", block.group(1)))
    if label not in found:
        raise AssertionError(f'business.ts 에 {label!r} 항목이 없습니다. 있는 것: {sorted(found)}')
    return found[label]


class SupportContactTests(TestCase):
    """
    사이트 하단 정보와 결제 화면의 연락처는 같은 값이어야 한다.

    심사는 사업자등록증·하단 정보·결제 화면을 나란히 놓고 본다. 두 곳에 따로
    적어 두면 한쪽만 고치는 날이 오고, 그날 심사가 반려된다.
    """

    def test_support_email_matches_the_site_footer(self):
        from django.conf import settings as django_settings

        self.assertEqual(django_settings.SUPPORT_EMAIL, _business_field('이메일'))

    def test_support_phone_matches_the_site_footer(self):
        from django.conf import settings as django_settings

        self.assertEqual(django_settings.SUPPORT_PHONE, _business_field('대표전화'))


class CheckoutConsentTests(TestCase):
    """
    약관 동의는 서버가 확인한다.

    템플릿의 required 는 브라우저에서만 막힌다. 심사는 '이용 조건이 이용자에게
    안내되었는지'를 보는데, 우회로 그냥 통과되면 안내했다고 말할 수 없다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.owner = User.objects.create_user(username='owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant)
        self.client.force_login(self.owner)
        self.url = '/moonlight/admin/billing/start/'

    def test_checkout_without_consent_is_rejected(self):
        response = self.client.post(self.url, {'plan': 'pro'}, follow=True)
        self.assertContains(response, '약관에 동의')

    def test_consent_failure_does_not_change_the_plan(self):
        self.client.post(self.url, {'plan': 'pro'}, follow=True)
        self.assertEqual(Subscription.objects.get(restaurant=self.restaurant).plan, 'entry')


class SupportContactFallbackTests(TestCase):
    """연락처를 아직 못 받았어도 결제 화면 문장이 깨지면 안 된다."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.owner = User.objects.create_user(username='owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant)
        self.client.force_login(self.owner)

    def _dispute_text(self):
        """'이의신청' 항목의 본문만 뽑는다."""
        body = self.client.get('/moonlight/admin/billing/').content.decode()
        section = re.search(r'이의신청</dt>\s*<dd>(.*?)</dd>', body, re.S)
        self.assertIsNotNone(section, '결제 화면에 이의신청 안내가 없습니다')
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', section.group(1))).strip()

    def test_contact_is_used_when_we_have_it(self):
        with self.settings(SUPPORT_EMAIL='help@example.com', SUPPORT_PHONE='02-000-0000'):
            text = self._dispute_text()
        self.assertIn('help@example.com', text)
        self.assertIn('02-000-0000', text)

    def test_missing_contact_falls_back_to_the_enquiry_page(self):
        """
        연락처가 비어 있으면 '  으로 알려주시면' 같은 구멍 난 문장이 나간다.
        심사자가 읽는 화면이고, 연락 방법이 없는 이의신청 안내는 안내가 아니다.
        """
        with self.settings(SUPPORT_EMAIL='', SUPPORT_PHONE=''):
            text = self._dispute_text()
        self.assertNotIn('  ', text)
        self.assertIn('문의', text)
        self.assertRegex(text, r'문의(하기|해)')


class PaymentPendingNoticeTests(TestCase):
    """
    연동 전 안내 문구.

    사실이어야 하고(요금이 청구되지 않는다), 동시에 '고장난 사이트'로 읽히면
    안 된다. 이 화면은 전자결제 심사자도 본다. 셀프가입 서비스인데 '담당자에게
    문의'라고 적혀 있으면 사장님도 어디로 문의하라는 건지 알 수 없다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.owner = User.objects.create_user(username='owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant)
        self.client.force_login(self.owner)

    def _body(self):
        return self.client.get('/moonlight/admin/billing/').content.decode()

    def test_notice_says_charges_are_not_made_yet(self):
        self.assertIn('청구되지 않습니다', self._body())

    def test_notice_does_not_send_the_owner_to_a_nonexistent_desk(self):
        self.assertNotIn('담당자에게 문의', self._body())
