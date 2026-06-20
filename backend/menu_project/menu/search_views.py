from django.http import JsonResponse
from django.db.models import Q
from .models import Category, MenuItem
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

def search_redirect_view(request, restaurant_slug=None):
    query = request.GET.get('q', '').strip()

    if not query:
        return redirect('menu:menu_main', restaurant_slug=request.restaurant.slug)

    # First, try to find an exact match (case-insensitive) in current restaurant
    menu_item = MenuItem.objects.filter(name__iexact=query, restaurant=request.restaurant).first()

    # If no exact match, try a contains match
    if not menu_item:
        menu_item = MenuItem.objects.filter(name__icontains=query, restaurant=request.restaurant).first()

    if menu_item:
        # If the item has a category, redirect to the category list page
        if menu_item.category:
            url = reverse('menu:menu_list', args=[request.restaurant.slug, menu_item.category.id])
            return redirect(f'{url}?target={menu_item.id}')
        else:
            messages.info(request, f"'{menu_item.name}' 메뉴를 찾았지만, 카테고리에 속해있지 않습니다.")
            return redirect('menu:menu_main', restaurant_slug=request.restaurant.slug)
    else:
        messages.warning(request, f"'{query}'에 해당하는 메뉴를 찾을 수 없습니다.")
        return redirect('menu:menu_main', restaurant_slug=request.restaurant.slug)


def search_api(request, restaurant_slug=None):
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    # 보안 강화: Pro/Standard 유저는 자기 가게 것만 볼 수 있어야 함
    # Superuser는 모든 가게 검색 가능
    target_restaurant = request.restaurant
    if request.user.is_authenticated and not request.user.is_superuser:
        if hasattr(request.user, 'profile') and request.user.profile.restaurant:
            # 프로필이 있는 유저라면 본인 가게로 강제 고정
            target_restaurant = request.user.profile.restaurant

    results = []
    
    # 카테고리 검색 (현재 레스토랑, 중복 방지, 인트로 카테고리 제외)
    categories = Category.objects.filter(
        Q(name__icontains=query),
        restaurant=target_restaurant
    ).exclude(name__icontains='인트로').distinct()[:5]
    
    for category in categories:
        results.append({
            'type': 'category',
            'title': category.name,
            'subtitle': '카테고리',
            'url': f'/{target_restaurant.slug}/category/{category.id}/'
        })
    
    # 메뉴 검색 (현재 레스토랑, 중복 방지)
    menu_items = MenuItem.objects.filter(
        Q(name__icontains=query) | 
        Q(name_en__icontains=query) | 
        Q(description__icontains=query),
        is_available=True,
        restaurant=target_restaurant
    ).distinct()[:5]
    
    for item in menu_items:
        price_raw = str(item.price)
        cleaned_price_for_check = price_raw.replace(',', '')
        if cleaned_price_for_check.replace('.', '', 1).isdigit():
            price_formatted = f"₩{price_raw}"
        else:
            price_formatted = price_raw

        results.append({
            'type': 'menu',
            'title': item.name,
            'subtitle': f'{item.category.name if item.category else "메뉴"} - {price_formatted}',
            'url': f'/{target_restaurant.slug}/category/{item.category.id}/#menu-{item.id}' if item.category else f'/{target_restaurant.slug}/#menu-{item.id}'
        })
    
    return JsonResponse({'results': results[:8]})