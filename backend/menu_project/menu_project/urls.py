from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from menu.qr_views import generate_qr_code
from menu import views as menu_views # 이 줄을 다시 추가합니다.
from menu import auth_views, billing_views, onboarding_views

admin.site.site_header = "bar-menu 통합 관리 시스템"
admin.site.site_title = "bar-menu 관리 포탈"
admin.site.index_title = "기본 DB 설정 관리"

urlpatterns = [
    path('admin/', admin.site.urls),
    # QR 코드 생성 등은 slug 없이 접근 가능하게 유지하거나 필요에 따라 slug 포함
    # path('qr/', generate_qr_code, name='qr_code'),  <-- 제거됨 (앱 URL에서 처리)
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico')),
    
    # REST API
    path('api/v1/', include('menu.api.urls')),
    
    # 메인 페이지 (매장 목록) — 기존 SSR (점진적 전환 시 유지)
    path('', menu_views.index_view, name='index'),
    
    # 제휴 문의 접수 — 기존 SSR
    path('contact-us/', menu_views.contact_us_view, name='contact_us'),

    # 셀프 가입 — 아직 매장이 없으니 slug 앞에 둘 수 없다
    path('signup/', onboarding_views.signup, name='signup'),
    path('signup/check-slug/', onboarding_views.check_slug, name='check_slug'),

    # 재방문 로그인. 사장님이 자기 매장 주소를 외우고 있을 거라 기대하지 않는다
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),

    # 결제 대행사가 호출하는 웹훅. 대행사별 서명 검증은 provider 가 맡는다
    path('billing/webhook/<str:provider>/', billing_views.webhook, name='billing_webhook'),
    
    # 식당별 URL (예: /bid/..., /cafe/...) — 기존 SSR
    path('<slug:restaurant_slug>/', include('menu.urls')),
]

# 미디어 파일 서빙 (폰트, 이미지 등 업로드 파일)
# 프로덕션에서도 미디어 파일을 서빙해야 함 (폰트 파일 포함)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 개발 환경에서 정적 파일 서빙 (프로덕션은 whitenoise가 처리)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
