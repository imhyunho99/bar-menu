from django.shortcuts import get_object_or_404
from django.utils.deprecation import MiddlewareMixin
from .models import Restaurant

class RestaurantMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # URL 패턴에서 'restaurant_slug' 인자가 있으면 추출
        slug = view_kwargs.get('restaurant_slug')
        
        # 시스템 경로나 정적 파일 등은 처리하지 않음 (성능 최적화)
        if request.path.startswith(('/static/', '/media/', '/admin/', '/favicon.ico')):
            request.restaurant = None
            return None
        
        if slug:
            # 해당 슬러그의 Restaurant 객체를 찾아서 request에 저장
            # 없으면 404 에러 발생 (get_object_or_404)
            request.restaurant = get_object_or_404(Restaurant, slug=slug)
        else:
            request.restaurant = None
            
        return None
