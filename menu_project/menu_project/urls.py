from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from menu.qr_views import generate_qr_code
from menu import views as menu_views # 이 줄을 다시 추가합니다.

urlpatterns = [
    path('admin/', admin.site.urls),
    # QR 코드 생성 등은 slug 없이 접근 가능하게 유지하거나 필요에 따라 slug 포함
    # path('qr/', generate_qr_code, name='qr_code'),  <-- 제거됨 (앱 URL에서 처리)
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico')),
    
    # 메인 페이지 (매장 목록)
    path('', menu_views.index_view, name='index'),
    
    # 식당별 URL (예: /bid/..., /cafe/...)
    path('<slug:restaurant_slug>/', include('menu.urls')),
]

# 미디어 파일 서빙 (폰트, 이미지 등 업로드 파일)
# 프로덕션에서도 미디어 파일을 서빙해야 함 (폰트 파일 포함)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 개발 환경에서 정적 파일 서빙 (프로덕션은 whitenoise가 처리)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
