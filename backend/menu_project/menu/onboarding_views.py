"""
셀프 가입과 가입 직후 온보딩 체크리스트.

지금까지 계정은 사람이 Django admin 에서 손으로 만들었다. 여기는 그 손을
빼는 자리다. 사장님이 마케팅 페이지에서 넘어와 폼 하나를 채우면 User ·
Restaurant · UserProfile · Subscription 네 덩어리가 한 트랜잭션에서 함께
생기고, 바로 로그인된 채 체크리스트로 떨어진다.
"""

import logging
import re

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse

from . import notifications
from .admin_views import check_restaurant_permission
from .models import Category, MenuItem, Restaurant, Subscription, UserProfile

logger = logging.getLogger(__name__)

# menu_project/urls.py 의 최상위 path() 에서 그대로 뽑은 목록.
# <slug:restaurant_slug> 는 urlpatterns 의 맨 끝이라, 앞에 놓인 이름과 같은
# slug 로 매장을 만들면 그 매장은 영원히 매칭되지 않는다. 가입 시점에 막지
# 않으면 사장님은 "주소가 안 열린다"는 사고를 개업 당일에 만난다.
#   admin        ← path('admin/', admin.site.urls)
#   favicon.ico  ← path('favicon.ico', RedirectView…)
#   api          ← path('api/v1/', include('menu.api.urls'))
#   contact-us   ← path('contact-us/', menu_views.contact_us_view)
#   signup       ← path('signup/'), path('signup/check-slug/')
#   login·logout ← path('login/'), path('logout/')
#   billing      ← path('billing/webhook/<str:provider>/')
#   static·media ← settings.STATIC_URL / MEDIA_URL (urlpatterns += static(...))
# 새 최상위 경로가 늘어나면 tests_onboarding 의 대조 테스트가 먼저 깨진다.
RESERVED_SLUGS = frozenset({
    'admin',
    'api',
    'billing',
    'contact-us',
    'favicon.ico',
    'login',
    'logout',
    'media',
    'signup',
    'static',
})

# django.urls.converters.SlugConverter.regex 와 같은 글자만 받는다.
# 여기서 통과시킨 글자를 URL 이 못 받으면 매장이 통째로 404 가 된다.
SLUG_RE = re.compile(r'^[-a-zA-Z0-9_]+$')

SLUG_MAX_LENGTH = Restaurant._meta.get_field('slug').max_length
NAME_MAX_LENGTH = Restaurant._meta.get_field('name').max_length

# 사장님에게 Django admin 의 디자인 기능을 열어 주는 권한 그룹. 실체는
# 마이그레이션 0053 이 만든다 — 이름만 여기서 참조한다.
OWNER_GROUP_NAME = '매장 사장님'
PHONE_MAX_LENGTH = UserProfile._meta.get_field('phone').max_length
USERNAME_MAX_LENGTH = User._meta.get_field('username').max_length


def validate_slug_value(slug):
    """
    매장 주소로 쓸 수 있는지 본다. 쓸 수 있으면 None, 아니면 한국어 사유.

    signup 과 check_slug 가 같은 함수를 쓴다. 실시간 안내와 실제 저장 규칙이
    갈리면 "초록불이었는데 가입이 안 된다"가 된다.
    """
    if not slug:
        return '매장 주소를 입력해 주세요.'
    if len(slug) > SLUG_MAX_LENGTH:
        return f'매장 주소는 {SLUG_MAX_LENGTH}자 이하로 입력해 주세요.'
    if not SLUG_RE.match(slug):
        return '매장 주소에는 영문·숫자·하이픈(-)·밑줄(_)만 쓸 수 있습니다.'
    if not re.search(r'[a-zA-Z0-9]', slug):
        return '매장 주소에 영문이나 숫자가 하나는 있어야 합니다.'
    if slug in RESERVED_SLUGS:
        return f"'{slug}'은(는) 시스템이 쓰는 주소라 매장 주소로 쓸 수 없습니다."
    # slug 자체는 대소문자를 구분해 저장되지만 주소로는 헷갈리기만 한다.
    # 이미 'Bid' 가 있는데 'bid' 를 또 내주면 둘 중 하나는 못 찾는 주소가 된다.
    if Restaurant.objects.filter(slug__iexact=slug).exists():
        return '이미 사용 중인 매장 주소입니다. 다른 주소를 입력해 주세요.'
    return None


def _validate_email_value(email):
    if not email:
        return '이메일을 입력해 주세요.'
    if len(email) > USERNAME_MAX_LENGTH:
        return f'이메일은 {USERNAME_MAX_LENGTH}자 이하로 입력해 주세요.'
    try:
        validate_email(email)
    except ValidationError:
        return '이메일 형식이 올바르지 않습니다.'
    # 이메일이 곧 아이디다. username 과 email 양쪽을 다 본다 —
    # 손으로 만든 기존 계정은 username 이 이메일이 아닐 수 있다.
    if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
        return '이미 가입된 이메일입니다.'
    return None


def _validate_password_value(password, email):
    if not password:
        return '비밀번호를 입력해 주세요.'
    try:
        # 저장 전이라 User 인스턴스가 없다. 아이디와 비슷한 비밀번호를
        # 걸러내려면 validator 에게 넘길 임시 객체가 필요하다.
        validate_password(password, User(username=email, email=email))
    except ValidationError as e:
        return ' '.join(e.messages)
    return None


def signup(request):
    """
    셀프 가입 한 화면. 성공하면 네 덩어리를 한 트랜잭션에 만들고 로그인시킨다.

    검증에 걸리면 입력값을 그대로 돌려준다. 매장명·주소를 다시 치게 만드는
    폼은 그 자리에서 이탈로 이어진다.
    """
    if request.method != 'POST':
        # 요금 페이지에서 넘어온 ?plan= 은 POST 까지 살아남아야 한다.
        # 폼 action 에는 쿼리가 안 붙으므로 히든 필드로 실어 보낸다.
        return render(request, 'onboarding/signup.html',
                      {'values': {}, 'errors': {}, 'plan': request.GET.get('plan', '')})

    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')
    name = request.POST.get('name', '').strip()
    # 선택 입력. 결제 대행사가 붙기 전까지 청구는 사람이 하고, 그 사람에게는
    # 전화가 이메일보다 잘 닿는다. 필수로 만들면 가입 폼에서 이탈한다.
    phone = request.POST.get('phone', '').strip()[:PHONE_MAX_LENGTH]
    # 주소는 소문자로 굳힌다. URL 은 대소문자를 구분하니 'Bid' 로 받아두면
    # 인쇄된 QR 이 /bid/ 를 가리키는 순간 404 다.
    slug = request.POST.get('slug', '').strip().lower()

    values = {'email': email, 'name': name, 'slug': slug, 'phone': phone}
    errors = {}

    error = _validate_email_value(email)
    if error:
        errors['email'] = error

    error = _validate_password_value(password, email)
    if error:
        errors['password'] = error

    if not name:
        errors['name'] = '매장명을 입력해 주세요.'
    elif len(name) > NAME_MAX_LENGTH:
        errors['name'] = f'매장명은 {NAME_MAX_LENGTH}자 이하로 입력해 주세요.'

    error = validate_slug_value(slug)
    if error:
        errors['slug'] = error

    if errors:
        return render(request, 'onboarding/signup.html', {'values': values, 'errors': errors}, status=400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                is_staff=True,  # 사장님이 관리 화면에 들어가려면 is_staff 가 있어야 한다
            )
            # is_staff 만으로는 /admin/ 이 빈 화면이다. 메뉴판 레이아웃 빌더와
            # 디자인 설정은 거기에만 있으므로 모델 권한까지 줘야 실제로 쓸 수 있다.
            # 그룹이 없으면(마이그레이션 전) 조용히 넘어간다 — 가입이 막히는 것보다 낫다.
            owner_group = Group.objects.filter(name=OWNER_GROUP_NAME).first()
            if owner_group:
                user.groups.add(owner_group)
            else:
                logger.error('%s 그룹이 없어 사장님에게 admin 권한을 주지 못했습니다', OWNER_GROUP_NAME)
            restaurant = Restaurant.objects.create(name=name, slug=slug)
            # SiteSettings 와 Subscription 은 Restaurant post_save 시그널이 이미
            # 만든다. 구독은 7일 무료 체험으로 시작하고, 체험이 끝나면 손님
            # 화면이 닫힌다(expire_trials 가 상태를 내리고 우리에게 알린다).
            UserProfile.objects.create(user=user, restaurant=restaurant, phone=phone)
            # 요금 페이지에서 요금제를 고르고 왔으면 그것으로 맞춰 둔다. 무시하면
            # Premium 을 고른 사장님이 아무 안내 없이 Entry 결제 화면을 만난다.
            # 모르는 값은 조용히 기본값으로 떨군다.
            wanted = request.GET.get('plan') or request.POST.get('plan') or ''
            valid_plans = {code for code, _ in Subscription.PLAN_CHOICES}
            if wanted in valid_plans:
                restaurant.subscription.plan = wanted
                restaurant.subscription.save(update_fields=['plan'])
    except IntegrityError:
        # validate 와 INSERT 사이에 같은 주소·이메일이 먼저 들어온 경우.
        # 유일 제약이 최종 심판이므로 여기서 폼으로 되돌린다.
        errors['slug'] = '방금 다른 분이 같은 주소로 가입했습니다. 다른 주소를 입력해 주세요.'
        return render(request, 'onboarding/signup.html', {'values': values, 'errors': errors}, status=400)

    # 트랜잭션 밖에서 알린다. 안에서 보내면 뒤늦은 롤백이 '가입했다' 는
    # 알림만 남긴다. 발송은 데몬 스레드라 실패해도 가입을 막지 않는다.
    notifications.send_signup_notification(restaurant)

    login(request, user)
    return redirect('menu:onboarding_home', restaurant_slug=restaurant.slug)


def check_slug(request):
    """가입 폼에서 타이핑 중에 부르는 주소 확인. signup 과 규칙을 공유한다."""
    slug = request.GET.get('slug', '').strip().lower()
    reason = validate_slug_value(slug)
    if reason:
        return JsonResponse({'available': False, 'reason': reason})
    return JsonResponse({'available': True, 'reason': f'/{slug} 주소를 쓸 수 있습니다.'})


def _site_settings_admin_url(site_settings):
    """디자인 설정은 아직 Django admin 이 유일한 편집 화면이다."""
    if site_settings is None:
        return None
    try:
        return reverse('admin:menu_sitesettings_change', args=[site_settings.pk])
    except NoReverseMatch:
        return None


def onboarding_home(request, restaurant_slug=None):
    """
    가입 직후 사장님이 보는 체크리스트.

    체크 표시는 전부 DB 를 읽어서 정한다. 고정으로 켜 두면 '했다고 나오는데
    손님 화면엔 없다'는 문의가 그대로 온다.
    """
    # LOGIN_URL 이 설정되어 있지 않아 @login_required 는 없는 /accounts/login/
    # 으로 보낸다. 가입 직후 화면에서 그 사고를 낼 수는 없으니 매장 로그인으로 보낸다.
    if not request.user.is_authenticated:
        return redirect('menu:admin_login', restaurant_slug=restaurant_slug)

    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("이 매장에 대한 관리 권한이 없습니다.")

    restaurant = request.restaurant
    category_count = Category.objects.filter(restaurant=restaurant).count()
    # 손님 화면은 카테고리를 타고 그려진다. 카테고리 없는 메뉴는 DB 에 있어도
    # 손님에게 닿지 않으므로 '등록됨'으로 세지 않는다. 여기서 세어 버리면
    # 체크는 켜져 있는데 메뉴판은 비어 있는 상태가 만들어진다.
    menu_count = MenuItem.objects.filter(restaurant=restaurant, category__isnull=False).count()
    site_settings = restaurant.site_settings.first()
    subscription = getattr(restaurant, 'subscription', None)

    # SiteSettings 행 자체는 Restaurant 생성 시그널이 항상 만들어 준다.
    # 그러니 '행이 있다'로 체크하면 늘 켜져 있는 가짜 체크가 된다.
    # 사장님이 실제로 손댔는지는 올린 이미지가 있는지로 본다.
    design_touched = bool(site_settings and (site_settings.logo_image or site_settings.intro_image))
    paid = bool(subscription and subscription.status == 'active')
    menu_is_live = bool(subscription and subscription.menu_is_live())

    steps = [
        {
            'key': 'menu',
            'title': '메뉴 등록',
            'done': menu_count > 0,
            'detail': (
                f'카테고리 {category_count}개 · 메뉴 {menu_count}개 등록됨'
                if menu_count else '아직 등록된 메뉴가 없습니다.'
            ),
            'primary_url': reverse('menu:import_menu', kwargs={'restaurant_slug': restaurant.slug}),
            'primary_label': '메뉴판 사진으로 등록',
            'secondary_url': reverse('menu:add_menu', kwargs={'restaurant_slug': restaurant.slug}),
            'secondary_label': '직접 입력',
        },
        {
            'key': 'qr',
            'title': 'QR 받기',
            # QR 은 내려받아도 DB 에 아무 흔적이 남지 않는다. 그래서 완료로
            # 표시할 근거가 없고, 대신 메뉴가 생겼는지로 준비 여부만 알린다.
            'done': False,
            'locked': menu_count == 0,
            'detail': (
                '테이블에 붙일 QR을 내려받으세요.'
                if menu_count else '메뉴를 먼저 등록하면 QR이 의미가 생깁니다.'
            ),
            'primary_url': reverse('menu:qr_code', kwargs={'restaurant_slug': restaurant.slug}),
            'primary_label': 'QR 코드 보기',
        },
        {
            'key': 'design',
            'title': '디자인 맞추기',
            'done': design_touched,
            'detail': (
                '로고·인트로 이미지가 등록되어 있습니다.'
                if design_touched else '로고와 인트로 이미지를 올리면 매장 분위기가 살아납니다.'
            ),
            'primary_url': _site_settings_admin_url(site_settings),
            'primary_label': '디자인 설정 열기',
        },
        {
            'key': 'billing',
            'title': '결제 등록',
            'done': paid,
            'detail': (
                '결제가 등록되어 있습니다.'
                if paid else '결제를 등록해야 손님이 메뉴판을 볼 수 있습니다.'
            ),
            'primary_url': reverse('menu:billing_home', kwargs={'restaurant_slug': restaurant.slug}),
            'primary_label': '결제 등록하기',
        },
    ]

    return render(request, 'onboarding/start.html', {
        'restaurant': restaurant,
        'steps': steps,
        'done_count': sum(1 for step in steps if step['done']),
        'total_count': len(steps),
        'subscription': subscription,
        'days_left': subscription.days_left if subscription else None,
        'menu_is_live': menu_is_live,
        # 결제 대행사가 붙기 전이라 배너의 행동 버튼은 문의로 간다.
        'contact_url': f'{settings.MARKETING_SITE_URL}/#contact',
        'menu_count': menu_count,
        'category_count': category_count,
    })
