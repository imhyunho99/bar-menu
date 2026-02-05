from django.shortcuts import render, get_object_or_404
from django.db.models import Case, When, IntegerField, Q
from django.http import JsonResponse
from .models import MenuItem, Category, SiteSettings, Restaurant

def index_view(request):
    """
    메인 페이지 (/) - 등록된 모든 레스토랑 목록 표시
    """
    restaurants = Restaurant.objects.all().order_by('name')
    return render(request, 'menu/index.html', {'restaurants': restaurants})

def get_breadcrumb_path(category):
    """카테고리의 전체 경로를 생성"""
    path = []
    current = category
    while current:
        path.insert(0, current)
        current = current.parent
    return path

def menu_main(request, restaurant_slug=None):
    # 최상위 카테고리만 가져오기 (parent가 None인 카테고리)
    # 현재 레스토랑 데이터만 필터링
    top_categories = Category.objects.filter(
        parent=None, 
        restaurant=request.restaurant
    ).order_by('priority', 'name')
    
    # 사이드 메뉴를 위해 모든 카테고리 가져오기
    # N+1 문제 해결: 사이드 메뉴 렌더링 시 sub_categories 접근함
    all_categories = Category.objects.filter(
        restaurant=request.restaurant
    ).prefetch_related('sub_categories').order_by('priority', 'name')
    
    # 사이트 설정에서 인트로 이미지 가져오기
    site_settings = SiteSettings.objects.filter(restaurant=request.restaurant).first()
    
    return render(request, 'menu/menu_main.html', {
        'categories': top_categories,
        'all_categories': all_categories,
        'site_settings': site_settings
    })

def menu_list(request, category_id, restaurant_slug=None):
    # 선택된 카테고리 (현재 레스토랑의 것인지 확인)
    # N+1 문제 해결: 템플릿에서 sub_categories 접근 가능성 있음
    category = get_object_or_404(
        Category.objects.prefetch_related('sub_categories'),
        id=category_id, 
        restaurant=request.restaurant
    )
    
    # 하위 카테고리 목록 (이미 prefetch 되었지만 명시적 쿼리셋이 필요할 경우를 위해 유지, 
    # 하지만 category.sub_categories.all()은 DB 히트 없이 캐시된 결과 사용 가능할 수 있음.
    # 단, .all()은 새로운 쿼리셋을 반환하므로 prefetch 결과를 쓰려면 .all() 대신 속성 접근 필요.
    # 여기서는 명시적 쿼리가 정렬 등을 위해 안전함)
    sub_categories = category.sub_categories.all().order_by('priority', 'name')
    breadcrumb_path = get_breadcrumb_path(category)
    
    # 모든 카테고리 가져오기 (사이드 메뉴용)
    all_categories = Category.objects.filter(
        restaurant=request.restaurant
    ).prefetch_related('sub_categories').order_by('priority', 'name')
    
    # 사이트 설정 가져오기
    site_settings = SiteSettings.objects.filter(restaurant=request.restaurant).first()
    
    # 하위 카테고리가 있으면 카테고리 페이지, 없으면 메뉴 페이지
    if sub_categories.exists():
        # 하위 카테고리가 있는 경우 - 카테고리 선택 페이지
        return render(request, 'menu/category_list.html', {
            'category': category,
            'categories': sub_categories,
            'breadcrumb_path': breadcrumb_path,
            'all_categories': all_categories,
            'site_settings': site_settings
        })
    else:
        # 최하위 카테고리인 경우 - 메뉴 표시 (우선순위 순으로 정렬)
        # N+1 문제 해결: 메뉴 아이템 조회 시 필요한 관계가 있다면 select_related 추가
        items = MenuItem.objects.filter(
            category=category, 
            is_available=True,
            restaurant=request.restaurant
        ).order_by('priority', 'name')
        
        # 순환 연결리스트: 모든 메뉴 아이템이 있는 카테고리를 하나의 리스트로 만들기
        # 우선순위와 이름 순으로 정렬하여 일관된 순서 보장
        all_menu_categories = Category.objects.filter(
            menu_items__is_available=True,
            restaurant=request.restaurant
        ).distinct().order_by('priority', 'name')
        
        # 순환 리스트로 변환
        menu_categories_list = list(all_menu_categories)
        
        # 현재 카테고리 인덱스 찾기
        current_index = None
        for i, cat in enumerate(menu_categories_list):
            if cat.id == category.id:
                current_index = i
                break
        
        # 순환 연결리스트 방식으로 다음/이전 카테고리 찾기
        prev_category = None
        next_category = None
        
        if current_index is not None and len(menu_categories_list) > 0:
            # 다음 카테고리: 현재 인덱스 + 1 (마지막이면 첫 번째로)
            next_index = (current_index + 1) % len(menu_categories_list)
            next_category = menu_categories_list[next_index]
            
            # 이전 카테고리: 현재 인덱스 - 1 (첫 번째이면 마지막으로)
            prev_index = (current_index - 1 + len(menu_categories_list)) % len(menu_categories_list)
            prev_category = menu_categories_list[prev_index]
            
            # 자기 자신만 있는 경우는 None 처리
            if len(menu_categories_list) == 1:
                prev_category = None
                next_category = None
        
        return render(request, 'menu/menu_list.html', {
            'category': category,
            'items': items,
            'breadcrumb_path': breadcrumb_path,
            'all_categories': all_categories,
            'site_settings': site_settings,
            'prev_category': prev_category,
            'next_category': next_category
        })