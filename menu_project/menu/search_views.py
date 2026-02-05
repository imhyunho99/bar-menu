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
    
    results = []
    
    # 카테고리 검색 (현재 레스토랑)
    categories = Category.objects.filter(
        Q(name__icontains=query),
        restaurant=request.restaurant
    )[:5]
    
    for category in categories:
        results.append({
            'type': 'category',
            'title': category.name,
            'subtitle': '카테고리',
            'url': f'/{request.restaurant.slug}/category/{category.id}/'
        })
    
    # 메뉴 검색 (현재 레스토랑)
    menu_items = MenuItem.objects.filter(
        Q(name__icontains=query) | 
        Q(name_en__icontains=query) | 
        Q(description__icontains=query),
        is_available=True,
        restaurant=request.restaurant
    )[:5]
    
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
            'url': f'/{request.restaurant.slug}/category/{item.category.id}/#menu-{item.id}' if item.category else f'/{request.restaurant.slug}/#menu-{item.id}'
        })
    
    return JsonResponse({'results': results[:8]})