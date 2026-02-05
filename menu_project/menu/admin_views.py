from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import Category, MenuItem, UserProfile, Restaurant

def check_restaurant_permission(user, restaurant_slug):
    """
    유저가 해당 레스토랑의 관리자 권한이 있는지 확인
    - Superuser는 무조건 True
    - 일반 유저는 본인의 profile.restaurant.slug와 일치해야 함
    """
    if user.is_superuser:
        return True
    
    if hasattr(user, 'profile') and user.profile.restaurant:
        return user.profile.restaurant.slug == restaurant_slug
    
    return False

def admin_login(request, restaurant_slug=None):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user and user.is_staff:
            login(request, user)
            
            # 로그인 성공 후 리다이렉트 로직
            # 1. Superuser: 현재 URL의 slug로 이동하거나, 없으면 첫 번째 식당으로 이동 (또는 선택 페이지)
            if user.is_superuser:
                target_slug = restaurant_slug or (Restaurant.objects.first().slug if Restaurant.objects.exists() else 'bid')
                return redirect('admin_dashboard', restaurant_slug=target_slug)
            
            # 2. 일반 관리자: 본인 소유의 식당으로 강제 리다이렉트
            if hasattr(user, 'profile') and user.profile.restaurant:
                return redirect('admin_dashboard', restaurant_slug=user.profile.restaurant.slug)
            else:
                messages.error(request, '관리할 수 있는 매장이 없습니다.')
                return redirect('admin_login')
                
        messages.error(request, '아이디 또는 비밀번호가 올바르지 않거나 권한이 없습니다.')
        
    return render(request, 'admin/login.html')

@login_required
def admin_dashboard(request, restaurant_slug=None):
    # 권한 체크
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("이 매장에 대한 관리 권한이 없습니다.")

    categories = Category.objects.filter(restaurant=request.restaurant).order_by('priority', 'name')
    menu_items = MenuItem.objects.filter(restaurant=request.restaurant).order_by('category__priority', 'priority', 'name')
    return render(request, 'admin/dashboard.html', {
        'categories': categories,
        'menu_items': menu_items
    })

@login_required
def add_category(request, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method == 'POST':
        name = request.POST['name']
        parent_id = request.POST.get('parent')
        parent = Category.objects.get(id=parent_id, restaurant=request.restaurant) if parent_id else None
        Category.objects.create(name=name, parent=parent, restaurant=request.restaurant)
        return redirect('admin_dashboard', restaurant_slug=request.restaurant.slug)
    categories = Category.objects.filter(parent=None, restaurant=request.restaurant)
    return render(request, 'admin/add_category.html', {'categories': categories})

@login_required
def add_menu(request, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method == 'POST':
        category_id = request.POST.get('category')
        # 카테고리 유효성 검사 (현재 식당의 카테고리인지)
        category = None
        if category_id:
             category = Category.objects.filter(id=category_id, restaurant=request.restaurant).first()

        MenuItem.objects.create(
            name=request.POST['name'],
            name_en=request.POST.get('name_en', ''),
            price=request.POST['price'],
            description=request.POST['description'],
            category=category,
            notes=request.POST.get('notes', ''),
            menu_image=request.FILES.get('image'),
            restaurant=request.restaurant
        )
        return redirect('admin_dashboard', restaurant_slug=request.restaurant.slug)
    categories = Category.objects.filter(restaurant=request.restaurant)
    return render(request, 'admin/menu_form.html', {'categories': categories, 'menu': None})

@login_required
def edit_menu(request, menu_id, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    menu = get_object_or_404(MenuItem, id=menu_id, restaurant=request.restaurant)
    if request.method == 'POST':
        menu.name = request.POST['name']
        menu.name_en = request.POST.get('name_en', '')
        menu.price = request.POST['price']
        menu.description = request.POST['description']
        
        category_id = request.POST.get('category')
        if category_id:
            menu.category = Category.objects.filter(id=category_id, restaurant=request.restaurant).first()
        else:
            menu.category = None
            
        menu.notes = request.POST.get('notes', '')
        if request.FILES.get('image'):
            menu.menu_image = request.FILES['image']
        menu.save()
        return redirect('admin_dashboard', restaurant_slug=request.restaurant.slug)
    categories = Category.objects.filter(restaurant=request.restaurant)
    return render(request, 'admin/menu_form.html', {'menu': menu, 'categories': categories})

@login_required
def delete_menu(request, menu_id, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    MenuItem.objects.filter(id=menu_id, restaurant=request.restaurant).delete()
    return redirect('admin_dashboard', restaurant_slug=request.restaurant.slug)

@login_required
def delete_category(request, category_id, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    Category.objects.filter(id=category_id, restaurant=request.restaurant).delete()
    return redirect('admin_dashboard', restaurant_slug=request.restaurant.slug)
