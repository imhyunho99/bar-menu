from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
import json
from .models import Category, MenuItem, UserProfile, Restaurant, Order, OrderItem, MenuItemPairing, SiteSettings
from .menu_import import MAX_UPLOAD_BYTES, MenuImportError, parse_menu_image

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
                return redirect('menu:admin_dashboard', restaurant_slug=target_slug)
            
            # 2. 일반 관리자: 본인 소유의 식당으로 강제 리다이렉트
            if hasattr(user, 'profile') and user.profile.restaurant:
                return redirect('menu:admin_dashboard', restaurant_slug=user.profile.restaurant.slug)
            else:
                messages.error(request, '관리할 수 있는 매장이 없습니다.')
                return redirect('menu:admin_login')
                
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
        name_en = request.POST.get('name_en', '')
        parent_id = request.POST.get('parent')
        parent = Category.objects.filter(id=parent_id, restaurant=request.restaurant).first() if parent_id else None
        
        priority = request.POST.get('priority')
        priority_val = float(priority) if priority else 0.0
        
        hide_side_image = request.POST.get('hide_side_image') == 'on'
        category_image = request.FILES.get('category_image')
        
        Category.objects.create(
            name=name,
            name_en=name_en,
            parent=parent,
            priority=priority_val,
            hide_side_image=hide_side_image,
            category_image=category_image,
            restaurant=request.restaurant
        )
        messages.success(request, f"카테고리 '{name}' 추가 완료되었습니다.")
        return redirect('menu:admin_dashboard', restaurant_slug=request.restaurant.slug)
        
    categories = Category.objects.filter(restaurant=request.restaurant)
    return render(request, 'admin/category_form.html', {
        'categories': categories,
        'category': None
    })

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
            display_mode=request.POST.get('display_mode', 'auto'),
            click_expand=request.POST.get('click_expand') == 'on',
            lightbox_style=request.POST.get('lightbox_style', 'zoom'),
            lightbox_opacity=int(request.POST.get('lightbox_opacity', 35) or 35),
            enable_detail_view=request.POST.get('enable_detail_view') == 'on',
            detail_image=request.FILES.get('detail_image'),
            detail_description=request.POST.get('detail_description', ''),
            restaurant=request.restaurant
        )
        return redirect('menu:admin_dashboard', restaurant_slug=request.restaurant.slug)
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
        
        menu.display_mode = request.POST.get('display_mode', 'auto')
        menu.click_expand = request.POST.get('click_expand') == 'on'
        menu.lightbox_style = request.POST.get('lightbox_style', 'zoom')
        menu.lightbox_opacity = int(request.POST.get('lightbox_opacity', 35) or 35)
        
        # 상세보기 설정
        menu.enable_detail_view = request.POST.get('enable_detail_view') == 'on'
        if request.FILES.get('detail_image'):
            menu.detail_image = request.FILES['detail_image']
        menu.detail_description = request.POST.get('detail_description', '')
        
        menu.save()
        return redirect('menu:admin_dashboard', restaurant_slug=request.restaurant.slug)
    categories = Category.objects.filter(restaurant=request.restaurant)
    return render(request, 'admin/menu_form.html', {'menu': menu, 'categories': categories})

@login_required
def delete_menu(request, menu_id, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    MenuItem.objects.filter(id=menu_id, restaurant=request.restaurant).delete()
    return redirect('menu:admin_dashboard', restaurant_slug=request.restaurant.slug)

@login_required
def delete_category(request, category_id, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    Category.objects.filter(id=category_id, restaurant=request.restaurant).delete()
    return redirect('menu:admin_dashboard', restaurant_slug=request.restaurant.slug)


@login_required
def edit_category(request, category_id, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    category = get_object_or_404(Category, id=category_id, restaurant=request.restaurant)
    if request.method == 'POST':
        category.name = request.POST['name']
        category.name_en = request.POST.get('name_en', '')
        parent_id = request.POST.get('parent')
        category.parent = Category.objects.filter(id=parent_id, restaurant=request.restaurant).first() if parent_id else None
        
        priority = request.POST.get('priority')
        if priority:
            category.priority = float(priority)
            
        category.hide_side_image = request.POST.get('hide_side_image') == 'on'
        
        if request.FILES.get('category_image'):
            category.category_image = request.FILES['category_image']
            
        category.save()
        messages.success(request, f"카테고리 '{category.name}' 수정 완료되었습니다.")
        return redirect('menu:admin_dashboard', restaurant_slug=request.restaurant.slug)

    categories = Category.objects.filter(restaurant=request.restaurant).exclude(id=category.id)
    return render(request, 'admin/category_form.html', {
        'category': category,
        'categories': categories
    })


@login_required
def duplicate_menu(request, menu_id, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    menu = get_object_or_404(MenuItem, id=menu_id, restaurant=request.restaurant)
    
    # 메뉴 복제
    new_menu = MenuItem.objects.get(id=menu_id)
    new_menu.id = None
    new_menu.pk = None
    new_menu.name = f"{new_menu.name} (복사본)"
    new_menu.priority = new_menu.priority + 0.1
    new_menu.save()

    # 페어링 복제
    for pairing in menu.pairings.all():
        new_pairing = MenuItemPairing.objects.get(id=pairing.id)
        new_pairing.id = None
        new_pairing.pk = None
        new_pairing.menu_item = new_menu
        new_pairing.save()

    messages.success(request, f"'{menu.name}' 메뉴 및 관련 주류 페어링이 복제되었습니다.")
    return redirect('menu:admin_dashboard', restaurant_slug=request.restaurant.slug)


@login_required
def import_menu(request, restaurant_slug=None):
    """
    종이 메뉴판 사진을 올려 항목을 뽑아낸다.

    뽑아낸 결과는 저장하지 않고 확인 화면으로 넘긴다. OCR이 가격 한 자리만
    틀려도 손님 화면이 틀어지므로, 사장님이 눈으로 보고 고친 뒤에 저장한다.
    """
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != 'POST':
        return render(request, 'admin/menu_import.html')

    upload = request.FILES.get('menu_image')
    if not upload:
        messages.error(request, '메뉴판 사진을 선택해 주세요.')
        return render(request, 'admin/menu_import.html')

    # read() 로 통째로 메모리에 올리기 전에 크기부터 본다
    if upload.size and upload.size > MAX_UPLOAD_BYTES:
        messages.error(
            request,
            f'사진이 너무 큽니다. {MAX_UPLOAD_BYTES // (1024 * 1024)}MB 이하로 올려 주세요.',
        )
        return render(request, 'admin/menu_import.html')

    try:
        parsed = parse_menu_image(upload.read())
    except MenuImportError as e:
        messages.error(request, str(e))
        return render(request, 'admin/menu_import.html')

    if not any(category.items for category in parsed.categories):
        messages.error(request, '사진에서 메뉴 항목을 찾지 못했습니다. 더 또렷한 사진으로 시도해 주세요.')
        return render(request, 'admin/menu_import.html')

    return render(request, 'admin/menu_import_preview.html', {
        'parsed': parsed,
        'existing_categories': Category.objects.filter(restaurant=request.restaurant).order_by('priority', 'name'),
    })


@login_required
@require_POST
def import_menu_commit(request, restaurant_slug=None):
    """확인 화면에서 손본 내용을 실제 카테고리·메뉴로 만든다."""
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    # 폼은 항목마다 c<카테고리번호>_i<항목번호> 로 이름을 붙인다.
    # 체크가 풀린 항목은 아예 전송되지 않으므로 include 목록이 곧 저장 대상이다.
    included = request.POST.getlist('include')
    if not included:
        messages.error(request, '저장할 항목을 하나 이상 선택해 주세요.')
        return redirect('menu:import_menu', restaurant_slug=request.restaurant.slug)

    # 이미 있는 카테고리에 붙일지, 새로 만들지는 카테고리 단위로 정해진다
    last_priority = (
        Category.objects.filter(restaurant=request.restaurant)
        .order_by('-priority')
        .values_list('priority', flat=True)
        .first()
    ) or 0.0

    created_categories = 0
    created_items = 0
    category_cache = {}

    # 이름을 비운 항목은 저장하지 않는다. 카테고리를 먼저 만들어 두면 그런
    # 항목만 있는 카테고리가 빈 채로 남으므로, 저장할 항목부터 추려낸다.
    included = [k for k in included if request.POST.get(f'{k}_name', '').strip()]
    if not included:
        messages.error(request, '저장할 항목의 메뉴명이 모두 비어 있습니다.')
        return redirect('menu:import_menu', restaurant_slug=request.restaurant.slug)

    for key in included:
        cat_idx = key.split('_')[0]

        if cat_idx not in category_cache:
            existing_id = request.POST.get(f'{cat_idx}_existing')
            if existing_id:
                category = Category.objects.filter(id=existing_id, restaurant=request.restaurant).first()
                # 남의 매장 카테고리이거나 그새 지워진 id. 그냥 두면 카테고리
                # 없는 메뉴가 조용히 생겨서 손님 화면 어디에도 안 뜬다.
                if category is None:
                    messages.error(request, '고른 카테고리를 찾을 수 없습니다. 다시 시도해 주세요.')
                    return redirect('menu:import_menu', restaurant_slug=request.restaurant.slug)
            else:
                last_priority += 1.0
                category = Category.objects.create(
                    name=request.POST.get(f'{cat_idx}_name', '').strip() or '메뉴',
                    name_en=request.POST.get(f'{cat_idx}_name_en', '').strip(),
                    priority=last_priority,
                    restaurant=request.restaurant,
                )
                created_categories += 1
            category_cache[cat_idx] = category

        category = category_cache[cat_idx]
        name = request.POST.get(f'{key}_name', '').strip()
        if not name:
            continue

        MenuItem.objects.create(
            name=name,
            name_en=request.POST.get(f'{key}_name_en', '').strip(),
            price=request.POST.get(f'{key}_price', '').strip(),
            description=request.POST.get(f'{key}_description', '').strip(),
            category=category,
            priority=float(created_items),
            restaurant=request.restaurant,
        )
        created_items += 1

    messages.success(
        request,
        f'메뉴 {created_items}개를 등록했습니다.'
        + (f' (카테고리 {created_categories}개 신규 생성)' if created_categories else '')
    )
    return redirect('menu:admin_dashboard', restaurant_slug=request.restaurant.slug)


@login_required
@require_POST
def reorder_categories(request, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return JsonResponse({'status': 'error', 'message': '권한이 없습니다.'}, status=403)

    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        for index, cat_id in enumerate(ids):
            Category.objects.filter(id=cat_id, restaurant=request.restaurant).update(priority=float(index))
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def reorder_menus(request, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return JsonResponse({'status': 'error', 'message': '권한이 없습니다.'}, status=403)

    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        for index, menu_id in enumerate(ids):
            MenuItem.objects.filter(id=menu_id, restaurant=request.restaurant).update(priority=float(index))
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def admin_orders(request, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    # 어드민 접속 IP를 감지하여 매장 설정의 공인 IP(store_public_ip)를 백그라운드 자동 갱신 (입력 제로 자동화)
    settings = request.restaurant.site_settings.first()
    if settings:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        client_ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')
        
        if client_ip not in ['127.0.0.1', '::1', 'localhost'] and not client_ip.startswith('::ffff:127.0.0.1'):
            if settings.store_public_ip != client_ip:
                settings.store_public_ip = client_ip
                settings.save(update_fields=['store_public_ip'])

    orders = Order.objects.filter(restaurant=request.restaurant).prefetch_related('items').order_by('-created_at')
    
    # AJAX로 새 주문 확인하는 요청 처리
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        latest_id = request.GET.get('latest_id')
        if latest_id:
            new_orders_count = Order.objects.filter(
                restaurant=request.restaurant, 
                id__gt=int(latest_id)
            ).count()
            return JsonResponse({'new_orders': new_orders_count > 0})

    return render(request, 'admin/orders.html', {
        'orders': orders,
        'latest_order_id': orders.first().id if orders.exists() else 0
    })


@login_required
@require_POST
def update_order_status(request, order_id, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return JsonResponse({'status': 'error', 'message': '권한이 없습니다.'}, status=403)

    order = get_object_or_404(Order, id=order_id, restaurant=request.restaurant)
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        if new_status in ['pending', 'completed', 'cancelled']:
            order.status = new_status
            order.save()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': '유효하지 않은 상태값입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
