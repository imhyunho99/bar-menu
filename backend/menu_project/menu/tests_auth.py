"""주소를 모르는 사장님이 자기 매장으로 돌아올 수 있는지."""

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Restaurant, UserProfile


class SluglessLoginTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.user = User.objects.create_user('owner@bar.kr', password='pw-that-is-long', is_staff=True)
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)

    def test_owner_lands_on_their_own_dashboard(self):
        response = self.client.post('/login/', {'email': 'owner@bar.kr', 'password': 'pw-that-is-long'})
        self.assertRedirects(
            response, f'/{self.restaurant.slug}/admin/dashboard/', fetch_redirect_response=False
        )

    def test_wrong_password_does_not_reveal_whether_the_account_exists(self):
        known = self.client.post('/login/', {'email': 'owner@bar.kr', 'password': 'nope'})
        unknown = self.client.post('/login/', {'email': 'ghost@bar.kr', 'password': 'nope'})

        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(
            known.content.decode().count('올바르지 않습니다'),
            unknown.content.decode().count('올바르지 않습니다'),
        )

    def test_entered_email_survives_a_failed_attempt(self):
        response = self.client.post('/login/', {'email': 'owner@bar.kr', 'password': 'nope'})
        self.assertIn('owner@bar.kr', response.content.decode())

    def test_non_staff_account_cannot_get_in(self):
        User.objects.create_user('guest@bar.kr', password='pw-that-is-long', is_staff=False)
        response = self.client.post('/login/', {'email': 'guest@bar.kr', 'password': 'pw-that-is-long'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_staff_account_without_a_restaurant_is_told_so(self):
        User.objects.create_user('orphan@bar.kr', password='pw-that-is-long', is_staff=True)
        response = self.client.post(
            '/login/', {'email': 'orphan@bar.kr', 'password': 'pw-that-is-long'}, follow=True
        )
        self.assertIn('연결된 매장이 없습니다', response.content.decode())

    def test_superuser_without_a_profile_lands_on_the_first_store(self):
        User.objects.create_superuser('root@bar.kr', password='pw-that-is-long')
        response = self.client.post('/login/', {'email': 'root@bar.kr', 'password': 'pw-that-is-long'})
        self.assertRedirects(
            response, f'/{self.restaurant.slug}/admin/dashboard/', fetch_redirect_response=False
        )

    def test_logout_returns_to_the_login_page(self):
        self.client.force_login(self.user)
        response = self.client.get('/logout/')
        self.assertRedirects(response, '/login/', fetch_redirect_response=False)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
