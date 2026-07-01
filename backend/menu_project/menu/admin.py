import json
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.http import require_POST
from .models import Restaurant, UserProfile, Category, MenuItem, SiteSettings, MenuItemPairing, ContactSubmission

class MenuItemPairingInline(admin.TabularInline):
    model = MenuItemPairing
    extra = 1
    classes = ('collapse',)

# UserProfile을 UserAdmin 페이지에 인라인으로 추가
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Restaurant Management Profile'

# 새로운 UserAdmin 정의
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

# 기존 UserAdmin 등록 해제 후 새로운 UserAdmin 등록
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# 공통 믹스인: 레스토랑별 데이터 격리
class RestaurantFilterMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile') and request.user.profile.restaurant:
            return qs.filter(restaurant=request.user.profile.restaurant)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if hasattr(request.user, 'profile') and request.user.profile.restaurant:
                obj.restaurant = request.user.profile.restaurant
        super().save_model(request, obj, form, change)

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return super().get_list_filter(request)
        # 일반 유저는 restaurant 필터 불필요 (어차피 하나만 보임)
        return [f for f in super().get_list_filter(request) if f != 'restaurant']

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [f for f in fields if f != 'restaurant']
        return fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.is_superuser:
            new_fieldsets = []
            for name, options in fieldsets:
                new_options = dict(options)
                if 'fields' in new_options:
                    new_options['fields'] = [f for f in new_options['fields'] if f != 'restaurant']
                new_fieldsets.append((name, new_options))
            return new_fieldsets
        return fieldsets

# Restaurant 모델 등록 (Superuser 전용)
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')
    
    def has_module_permission(self, request):
        # 일반 유저는 Restaurant 모델 관리 메뉴 자체를 안 보이게 설정
        return request.user.is_superuser

# 기존 모델들도 Admin에 등록
@admin.register(Category)
class CategoryAdmin(RestaurantFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'parent', 'priority')
    list_filter = ('restaurant',) # Superuser에게만 보임 (Mixin 처리)
    list_editable = ('parent', 'priority')
    ordering = ('priority',)

    class Media:
        js = ('js/admin_sortable.js',)

    def get_urls(self):
        custom_urls = [
            path('reorder/', self.admin_site.admin_view(self.reorder_view), name='category-reorder'),
        ]
        return custom_urls + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        # 1. 관리 가능한 레스토랑 목록 가져오기 (Superuser용)
        restaurants = Restaurant.objects.all().order_by('name')
        
        # 2. 현재 선택된 레스토랑 가져오기
        selected_restaurant = None
        if request.user.is_superuser:
            restaurant_id = request.GET.get('restaurant')
            if restaurant_id:
                selected_restaurant = Restaurant.objects.filter(id=restaurant_id).first()
            if not selected_restaurant:
                selected_restaurant = restaurants.first()
        else:
            if hasattr(request.user, 'profile') and request.user.profile.restaurant:
                selected_restaurant = request.user.profile.restaurant
        
        # 3. 카테고리 트리 데이터 구성
        workspace_data = get_menu_workspace_data(selected_restaurant)
        
        # 4. 컨텍스트 추가
        extra_context = extra_context or {}
        extra_context.update({
            'restaurants': restaurants if request.user.is_superuser else None,
            'selected_restaurant': selected_restaurant,
            'workspace_data': workspace_data,
            'title': '매장 카테고리 구조 관리',
        })
        
        return super().changelist_view(request, extra_context=extra_context)

    def reorder_view(self, request):
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            for index, cat_id in enumerate(ids):
                Category.objects.filter(id=cat_id).update(priority=float(index))
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

class RestaurantCategoryFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.restaurant:
            allowed_category_ids = set(
                Category.objects.filter(restaurant=request.user.profile.restaurant).values_list('id', flat=True)
            )
            self.lookup_choices = [
                choice for choice in self.lookup_choices 
                if choice[0] in allowed_category_ids
            ]


def get_menu_workspace_data(restaurant):
    if not restaurant:
        return {'top_categories': [], 'no_category_items': []}
    
    categories = Category.objects.filter(restaurant=restaurant).order_by('priority', 'name')
    menu_items = MenuItem.objects.filter(restaurant=restaurant).order_by('priority', 'name')
    
    category_map = {}
    top_categories = []
    
    for cat in categories:
        cat_data = {
            'id': cat.id,
            'name': cat.name,
            'name_en': cat.name_en or '',
            'priority': cat.priority,
            'parent_id': cat.parent_id,
            'sub_categories': [],
            'menu_items': []
        }
        category_map[cat.id] = cat_data
        if not cat.parent_id:
            top_categories.append(cat_data)
            
    for cat in categories:
        if cat.parent_id:
            parent = category_map.get(cat.parent_id)
            if parent:
                parent['sub_categories'].append(category_map[cat.id])
                
    no_category_items = []
    for item in menu_items:
        item_data = {
            'id': item.id,
            'name': item.name,
            'name_en': item.name_en or '',
            'price': str(item.price),
            'priority': item.priority,
            'is_available': item.is_available,
            'display_mode': item.display_mode,
            'image_url': item.menu_image.url if item.menu_image else ''
        }
        if item.category_id and item.category_id in category_map:
            category_map[item.category_id]['menu_items'].append(item_data)
        else:
            no_category_items.append(item_data)
            
    return {
        'top_categories': top_categories,
        'no_category_items': no_category_items
    }

@admin.register(MenuItem)
class MenuItemAdmin(RestaurantFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'price', 'display_mode', 'is_available', 'priority')
    list_filter = ('restaurant', ('category', RestaurantCategoryFilter), 'is_available', 'display_mode')
    list_editable = ('category', 'priority')
    search_fields = ('name', 'description')
    ordering = ('category', 'priority')
    inlines = [MenuItemPairingInline]
    fieldsets = (
        ('기본 정보', {
            'fields': ('restaurant', 'name', 'name_en', 'price', 'description', 'category', 'notes', 'menu_image', 'priority', 'is_available')
        }),
        ('표시 설정', {
            'fields': ('display_mode', 'click_expand', 'lightbox_style', 'lightbox_opacity'),
            'classes': ('collapse',),
            'description': '메뉴 카드의 표시 방식을 설정합니다.',
        }),
        ('상세보기 설정', {
            'fields': ('enable_detail_view', 'detail_image', 'detail_description'),
            'classes': ('collapse',),
            'description': '메뉴 클릭 시 표시될 상세 모달의 내용을 설정합니다.',
        }),
    )

    class Media:
        js = ('js/admin_sortable.js',)

    def get_urls(self):
        custom_urls = [
            path('reorder/', self.admin_site.admin_view(self.reorder_view), name='menuitem-reorder'),
            path('bulk-duplicate/', self.admin_site.admin_view(self.bulk_duplicate_view), name='menuitem-bulk-duplicate'),
            path('bulk-delete/', self.admin_site.admin_view(self.bulk_delete_view), name='menuitem-bulk-delete'),
            path('bulk-move/', self.admin_site.admin_view(self.bulk_move_view), name='menuitem-bulk-move'),
            path('<path:object_id>/duplicate/', self.admin_site.admin_view(self.duplicate_view), name='menuitem-duplicate'),
            path('<path:object_id>/toggle-available/', self.admin_site.admin_view(self.toggle_available_view), name='menuitem-toggle-available'),
        ]
        return custom_urls + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        # 1. 관리 가능한 레스토랑 목록 가져오기 (Superuser용)
        restaurants = Restaurant.objects.all().order_by('name')
        
        # 2. 현재 선택된 레스토랑 가져오기
        selected_restaurant = None
        if request.user.is_superuser:
            restaurant_id = request.GET.get('restaurant')
            if restaurant_id:
                selected_restaurant = Restaurant.objects.filter(id=restaurant_id).first()
            if not selected_restaurant:
                selected_restaurant = restaurants.first()
        else:
            if hasattr(request.user, 'profile') and request.user.profile.restaurant:
                selected_restaurant = request.user.profile.restaurant
        
        # 3. 워크스페이스 데이터 구성
        workspace_data = get_menu_workspace_data(selected_restaurant)
        
        # 4. 컨텍스트 추가
        extra_context = extra_context or {}
        extra_context.update({
            'restaurants': restaurants if request.user.is_superuser else None,
            'selected_restaurant': selected_restaurant,
            'workspace_data': workspace_data,
            'title': '매장 카테고리 & 메뉴 통합 관리',
        })
        
        return super().changelist_view(request, extra_context=extra_context)

    def reorder_view(self, request):
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            for index, menu_id in enumerate(ids):
                MenuItem.objects.filter(id=menu_id).update(priority=float(index))
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    def duplicate_view(self, request, object_id):
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)
        try:
            original = MenuItem.objects.get(id=object_id)
            pairings = list(original.pairings.all())
            original.pk = None
            original.id = None
            original.name = f"{original.name} (복사본)"
            original.priority = original.priority + 0.1
            original.save()
            for pairing in pairings:
                pairing.pk = None
                pairing.id = None
                pairing.menu_item = original
                pairing.save()
            return JsonResponse({'status': 'success', 'new_id': original.id})
        except MenuItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '메뉴를 찾을 수 없습니다.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    def toggle_available_view(self, request, object_id):
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)
        try:
            item = MenuItem.objects.get(id=object_id)
            if not request.user.is_superuser:
                if hasattr(request.user, 'profile') and request.user.profile.restaurant:
                    if item.restaurant != request.user.profile.restaurant:
                        return JsonResponse({'status': 'error', 'message': '권한이 없습니다.'}, status=403)
            item.is_available = not item.is_available
            item.save(update_fields=['is_available'])
            return JsonResponse({'status': 'success', 'is_available': item.is_available})
        except MenuItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '메뉴를 찾을 수 없습니다.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    def bulk_duplicate_view(self, request):
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            for obj_id in ids:
                original = MenuItem.objects.get(id=obj_id)
                pairings = list(original.pairings.all())
                original.pk = None
                original.id = None
                original.name = f"{original.name} (복사본)"
                original.priority = original.priority + 0.1
                original.save()
                for pairing in pairings:
                    pairing.pk = None
                    pairing.id = None
                    pairing.menu_item = original
                    pairing.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    def bulk_delete_view(self, request):
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            MenuItem.objects.filter(id__in=ids).delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    def bulk_move_view(self, request):
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            category_id = data.get('category_id')
            
            if category_id == 'none' or not category_id:
                category = None
            else:
                category = Category.objects.get(id=category_id)
                if not request.user.is_superuser:
                    if hasattr(request.user, 'profile') and request.user.profile.restaurant:
                        if category.restaurant != request.user.profile.restaurant:
                            return JsonResponse({'status': 'error', 'message': '권한이 없습니다.'}, status=403)
            
            MenuItem.objects.filter(id__in=ids).update(category=category)
            return JsonResponse({'status': 'success'})
        except Category.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '카테고리를 찾을 수 없습니다.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category" and not request.user.is_superuser:
            if hasattr(request.user, 'profile') and request.user.profile.restaurant:
                kwargs["queryset"] = Category.objects.filter(restaurant=request.user.profile.restaurant)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(SiteSettings)
class SiteSettingsAdmin(RestaurantFilterMixin, admin.ModelAdmin):
    list_display = ('restaurant', 'created_at')
    fieldsets = (
        ('기본 설정', {
            'fields': ('restaurant', 'logo_image', 'intro_image', 'intro_video', 'loading_video_2', 'show_manual_card', 'side_image')
        }),
        ('와이파이 및 결제 연동 설정', {
            'fields': ('enable_wifi', 'wifi_ssid', 'wifi_password', 'wifi_security', 'restrict_by_ip', 'store_public_ip', 'restrict_by_wifi_ssid', 'disable_screenshots', 'enable_payhere', 'enable_cart', 'payhere_store_id', 'payhere_api_key'),
        }),
        ('색상 설정', {
            'fields': ('background_color', 'category_card_color', 'menu_card_color'),
            'classes': ('collapse',),
        }),
        ('메뉴명(한글) 스타일', {
            'fields': ('menu_name_font', 'menu_name_color', 'menu_name_size', 'menu_name_bold', 'menu_name_italic'),
            'classes': ('collapse',),
        }),
        ('메뉴명(영문) 스타일', {
            'fields': ('menu_name_en_font', 'menu_name_en_color', 'menu_name_en_size', 'menu_name_en_bold', 'menu_name_en_italic'),
            'classes': ('collapse',),
        }),
        ('가격 스타일', {
            'fields': ('menu_price_font', 'menu_price_color', 'menu_price_size', 'menu_price_bold', 'menu_price_italic'),
            'classes': ('collapse',),
        }),
        ('메뉴 설명 스타일', {
            'fields': ('menu_description_font', 'menu_description_color', 'menu_description_size', 'menu_description_bold', 'menu_description_italic'),
            'classes': ('collapse',),
        }),
        ('기타 사항 스타일', {
            'fields': ('menu_notes_font', 'menu_notes_color', 'menu_notes_size', 'menu_notes_bold', 'menu_notes_italic'),
            'classes': ('collapse',),
        }),
        ('카테고리명(한글) 스타일', {
            'fields': ('category_name_font', 'category_name_color', 'category_name_size', 'category_name_bold', 'category_name_italic'),
            'classes': ('collapse',),
        }),
        ('카테고리명(영문) 스타일', {
            'fields': ('category_name_en_font', 'category_name_en_color', 'category_name_en_size', 'category_name_en_bold', 'category_name_en_italic'),
            'classes': ('collapse',),
        }),
        ('페어링명 스타일', {
            'fields': ('pairing_name_font', 'pairing_name_color', 'pairing_name_size', 'pairing_name_bold', 'pairing_name_italic'),
            'classes': ('collapse',),
        }),
        ('페어링 설명 스타일', {
            'fields': ('pairing_description_font', 'pairing_description_color', 'pairing_description_size', 'pairing_description_bold', 'pairing_description_italic'),
            'classes': ('collapse',),
        }),
        ('페어링 가격 스타일', {
            'fields': ('pairing_price_font', 'pairing_price_color', 'pairing_price_size', 'pairing_price_bold', 'pairing_price_italic'),
            'classes': ('collapse',),
        }),
    )
    
    def has_add_permission(self, request):
        # 이미 설정이 있다면 추가 불가능하게 (1:1 관계처럼 유지)
        if not request.user.is_superuser:
            if hasattr(request.user, 'profile') and request.user.profile.restaurant:
                if SiteSettings.objects.filter(restaurant=request.user.profile.restaurant).exists():
                    return False
        return super().has_add_permission(request)




@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'plan', 'created_at')
    search_fields = ('name', 'contact_info', 'plan')
    list_filter = ('plan', 'created_at')



