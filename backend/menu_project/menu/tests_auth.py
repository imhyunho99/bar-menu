"""주소를 모르는 사장님이 자기 매장으로 돌아올 수 있는지."""

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Restaurant, UserProfile


class SluglessLoginTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.user = User.objects.create_user('owner@bar.kr', password='pw-that-is-long', is_staff=True)
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)

    def test_owner_lands_in_the_admin(self):
        """
        디자인 빌더와 메뉴 편집이 둘 다 /admin/ 에 있다. 예전처럼 커스텀
        대시보드로 보내면 사장님은 디자인을 고치려고 다시 건너가야 했다.
        """
        response = self.client.post('/login/', {'email': 'owner@bar.kr', 'password': 'pw-that-is-long'})
        self.assertRedirects(response, '/admin/', fetch_redirect_response=False)

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

    def test_superuser_without_a_profile_gets_in_too(self):
        User.objects.create_superuser('root@bar.kr', password='pw-that-is-long')
        response = self.client.post('/login/', {'email': 'root@bar.kr', 'password': 'pw-that-is-long'})
        self.assertRedirects(response, '/admin/', fetch_redirect_response=False)

    def test_the_admin_home_still_points_at_the_screens_left_behind(self):
        """
        주문·결제·QR 은 아직 /<slug>/admin/ 에 있다. /admin/ 을 집으로 삼았으니
        여기서 그리로 가는 길이 없으면 사장님은 그 기능들을 잃어버린다.
        """
        self.client.force_login(self.user)
        page = self.client.get('/admin/').content.decode()
        for path in (f'/{self.restaurant.slug}/admin/orders/',
                     f'/{self.restaurant.slug}/admin/billing/',
                     f'/{self.restaurant.slug}/qr/'):
            self.assertIn(path, page)

    def test_a_superuser_home_does_not_break_without_stores(self):
        """매장이 하나도 없는 새 배포에서 첫 로그인이 500 이 되면 안 된다."""
        Restaurant.objects.all().delete()
        User.objects.create_superuser('root2@bar.kr', password='pw-that-is-long')
        self.client.login(username='root2@bar.kr', password='pw-that-is-long')
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_logout_returns_to_the_login_page(self):
        self.client.force_login(self.user)
        response = self.client.get('/logout/')
        self.assertRedirects(response, '/login/', fetch_redirect_response=False)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class TheAdminDoorTellsYouWhatWentWrongTests(TestCase):
    """
    /admin/ 이 사장님의 집이 되면서 /admin/login/ 이 정문이 됐다.

    이 문은 menu/templates/admin/login.html 이 그리는데, 그 파일은 원래
    /<slug>/admin/login/ 용으로 만들어졌고 실패를 messages 로만 읽는다.
    Django admin 은 실패를 form.errors 로 돌려주므로 그대로 두면 비밀번호가
    틀려도 화면에 아무 말이 없다 — 되는지 안 되는지 모른 채 같은 걸 다시 친다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.user = User.objects.create_user('owner@bar.kr', password='pw-that-is-long', is_staff=True)
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)

    def test_a_wrong_password_says_so(self):
        response = self.client.post('/admin/login/', {'username': 'owner@bar.kr', 'password': 'nope'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '올바르지 않습니다')

    def test_logging_in_goes_where_you_were_headed(self):
        """
        next 를 안 실으면 로그인은 되는데 LOGIN_REDIRECT_URL 기본값인
        /accounts/profile/ 로 가서 404 가 뜬다. 로그인에 성공하고 404 를 보는
        건 실패보다 나쁘다 — 뭘 고쳐야 할지 알 수 없다.
        """
        response = self.client.post(
            '/admin/login/?next=/admin/menu/menuitem/',
            {'username': 'owner@bar.kr', 'password': 'pw-that-is-long',
             'next': '/admin/menu/menuitem/'},
        )
        self.assertRedirects(response, '/admin/menu/menuitem/', fetch_redirect_response=False)
