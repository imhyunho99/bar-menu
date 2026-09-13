import json
from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.views.decorators.http import require_POST
from .admin_views import relay_menu_photos
from .models import (Restaurant, UserProfile, Category, MenuItem, SiteSettings,
                     MenuItemPairing, ContactSubmission, PaymentRequest, Subscription)

# 로그인한 사장님이 도착하는 화면. 기본 index 위에 아직 /<slug>/admin/ 에 남아
# 있는 주문·결제·QR 로 가는 줄을 얹는다. 이름이 index.html 이 아닌 이유는
# admin/owner_index.html 의 주석에 적어 뒀다.
admin.site.index_template = 'admin/owner_index.html'


class LayoutBuilderWidget(forms.Textarea):
    template_name = 'admin/widgets/layout_builder_widget.html'

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

def selected_restaurant_for(request):
    """
    지금 화면이 다루는 매장.

    사장님은 계정에 매장이 하나 묶여 있어 고를 일이 없다. 슈퍼유저는 매장이
    여럿이라 ?restaurant=<id> 로 고르고, 안 고르면 첫 매장을 본다.

    한 군데에 모아 둔 이유: 메뉴 워크스페이스와 그 안의 '사진으로 등록' 버튼이
    규칙을 따로 쓰면, 고른 매장과 사진이 날아가는 매장이 어긋난다. 그 어긋남은
    화면에 아무 표시도 남기지 않는다.
    """
    if request.user.is_superuser:
        # isdigit() 로 거르는 이유: 숫자가 아닌 값을 id 로 넘기면 Django 가
        # ValueError 를 던져 500 이 된다. 주소창을 손으로 고치면 나는 에러이고,
        # 로그인 도착지가 /admin/ 이 된 뒤로는 첫 화면이 통째로 죽는다.
        restaurant_id = request.GET.get('restaurant', '')
        if restaurant_id.isdigit():
            chosen = Restaurant.objects.filter(id=restaurant_id).first()
            if chosen:
                return chosen
        return Restaurant.objects.order_by('name').first()

    profile = getattr(request.user, 'profile', None)
    return profile.restaurant if profile else None


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
        restaurants = Restaurant.objects.all().order_by('name')
        selected_restaurant = selected_restaurant_for(request)

        # 카테고리 트리 데이터 구성
        workspace_data = get_menu_workspace_data(selected_restaurant)
        
        # 컨텍스트 추가
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
            # get_queryset 을 거친다. 화면은 id 만 보내오므로, 그 id 가 누구
            # 것인지 여기서 안 보면 개발자도구로 숫자만 바꿔 남의 매장을
            # 건드릴 수 있다. 목록에 안 보이는 것과 못 건드리는 것은 다르다.
            mine = self.get_queryset(request)
            for index, cat_id in enumerate(ids):
                mine.filter(id=cat_id).update(priority=float(index))
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
            path('import/', self.admin_site.admin_view(self.import_photos_view), name='menuitem-import-photos'),
        ]
        return custom_urls + super().get_urls()

    def import_photos_view(self, request):
        """
        메뉴판 사진 등록. 화면과 규칙은 /<slug>/admin/ 쪽과 같은 것을 쓴다.

        여기까지 온 계정은 admin_view 를 통과했으니 스태프인 것만 확실하다.
        매장이 안 묶인 스태프 계정이 실제로 있고, 그 사람에게 조용히 첫 매장을
        집어 주면 남의 매장 메뉴판이 우리에게 날아온다. 그래서 거절한다.
        """
        restaurant = selected_restaurant_for(request)
        if restaurant is None:
            raise PermissionDenied('관리할 매장이 없는 계정입니다.')

        workspace = reverse('admin:menu_menuitem_changelist')
        # 슈퍼유저는 매장을 골라서 들어온다. 그 선택을 안 물고 돌아가면
        # 고른 매장과 돌아간 매장이 어긋난다.
        if request.user.is_superuser:
            workspace += f'?restaurant={restaurant.id}'
        return relay_menu_photos(
            request,
            restaurant,
            'admin/menu_import_admin.html',
            cancel_url=workspace,
            success_url=workspace,
            extra_context={
                **self.admin_site.each_context(request),
                'title': '메뉴판 사진으로 등록',
            },
        )

    def changelist_view(self, request, extra_context=None):
        restaurants = Restaurant.objects.all().order_by('name')
        selected_restaurant = selected_restaurant_for(request)

        # 워크스페이스 데이터 구성
        workspace_data = get_menu_workspace_data(selected_restaurant)
        
        # 컨텍스트 추가
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
            mine = self.get_queryset(request)   # 남의 매장 id 는 여기서 걸러진다
            for index, menu_id in enumerate(ids):
                mine.filter(id=menu_id).update(priority=float(index))
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    def duplicate_view(self, request, object_id):
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)
        try:
            original = self.get_queryset(request).get(id=object_id)
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
            mine = self.get_queryset(request)
            for obj_id in ids:
                original = mine.get(id=obj_id)
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
            # 가장 되돌리기 어려운 동작이다. 섞여 들어온 남의 매장 id 는
            # 조용히 빠지고 내 것만 지워진다.
            self.get_queryset(request).filter(id__in=ids).delete()
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
            
            # 고른 카테고리가 내 것인지는 위에서 봤다. 옮기는 대상이 누구
            # 것인지도 봐야 한다 — 안 그러면 남의 메뉴가 내 카테고리로 온다.
            self.get_queryset(request).filter(id__in=ids).update(category=category)
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
    readonly_fields = ('sync_ip_button',)
    # 카드 레이아웃 빌더는 여기 없다. 저장과 API 전송까지는 되는데 손님 화면이
    # 그 JSON 을 읽지 않아서(frontend 에 참조 0건), 사장님이 배치를 옮기고
    # 저장해도 아무 일도 일어나지 않는다. 연결은 별도 스펙에서 만든다
    # (docs/superpowers/specs/2026-09-12-layout-renderer-design.md).
    # 그때까지 열어 두면 무료 티어의 핵심 화면이 조용히 거짓말을 한다.
    #
    # formfield_for_dbfield 의 LayoutBuilderWidget 분기는 그대로 둔다 —
    # 필드를 다시 노출하는 날 위젯이 같이 살아나야 한다.
    fieldsets = (
        ('기본 설정', {
            'fields': ('restaurant', 'logo_image', 'intro_image', 'intro_video', 'loading_video_2', 'show_manual_card', 'side_image')
        }),
        ('와이파이 및 결제 연동 설정', {
            'fields': ('enable_wifi', 'wifi_ssid', 'wifi_password', 'wifi_security', 'restrict_by_ip', 'store_public_ip', 'sync_ip_button', 'restrict_by_wifi_ssid', 'disable_screenshots', 'enable_payhere', 'enable_cart', 'payhere_store_id', 'payhere_api_key'),
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
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ['category_card_layout_json', 'menu_card_layout_json']:
            kwargs['widget'] = LayoutBuilderWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def has_add_permission(self, request):
        # 이미 설정이 있다면 추가 불가능하게 (1:1 관계처럼 유지)
        if not request.user.is_superuser:
            if hasattr(request.user, 'profile') and request.user.profile.restaurant:
                if SiteSettings.objects.filter(restaurant=request.user.profile.restaurant).exists():
                    return False
        return super().has_add_permission(request)

    def get_urls(self):
        # 매장 공인 IP를 현재 접속 IP로 동기화하는 커스텀 admin URL
        custom = [
            path(
                '<path:object_id>/sync-store-ip/',
                self.admin_site.admin_view(self.sync_store_ip),
                name='menu_sitesettings_sync_store_ip',
            ),
        ]
        return custom + super().get_urls()

    def sync_store_ip(self, request, object_id, *args, **kwargs):
        # 버튼을 누른 관리자의 현재 공인 IP를 store_public_ip에 저장한다.
        obj = self.get_object(request, object_id)  # get_queryset 스코핑 → 타 매장 접근 차단
        if obj is None:
            self.message_user(request, '설정을 찾을 수 없습니다.', level=messages.ERROR)
            return redirect('admin:menu_sitesettings_changelist')
        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        client_ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR', '')
        # ::ffff: IPv4-mapped IPv6 접두사 제거 (프론트 게이트 layout.tsx와 값 형식 일치)
        if client_ip.startswith('::ffff:'):
            client_ip = client_ip[7:]

        if client_ip and client_ip not in ('127.0.0.1', '::1', 'localhost'):
            obj.store_public_ip = client_ip
            obj.save(update_fields=['store_public_ip'])
            self.message_user(
                request,
                f'매장 공인 IP를 현재 접속 IP({client_ip})로 동기화했습니다.',
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                f'로컬/내부 접속(IP: {client_ip or "알 수 없음"})이라 동기화하지 않았습니다. '
                f'매장 와이파이에 연결한 기기에서 다시 눌러 주세요.',
                level=messages.WARNING,
            )
        return redirect('admin:menu_sitesettings_change', obj.pk)

    def sync_ip_button(self, obj):
        if not obj or not obj.pk:
            return '설정을 먼저 저장한 뒤 사용할 수 있습니다.'
        url = reverse('admin:menu_sitesettings_sync_store_ip', args=[obj.pk])
        current = obj.store_public_ip or '(미설정)'
        return format_html(
            '<a class="button" href="{}" style="background:#3b82f6;color:#fff;">현재 접속 IP로 동기화</a>'
            '<span style="margin-left:10px;color:#555;">저장된 매장 IP: <b>{}</b></span>'
            '<p class="help" style="margin-top:6px;">매장 와이파이에 연결한 기기에서 이 버튼을 누르면 현재 공인 IP가 매장 IP로 저장됩니다. '
            '위 <b>공인 IP 접속 제한</b>이 켜져 있으면, 이 IP로 접속할 때만 메뉴판이 보입니다.</p>',
            url, current,
        )
    sync_ip_button.short_description = '매장 공인 IP 동기화'




@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'plan', 'created_at')
    search_fields = ('name', 'contact_info', 'plan')
    list_filter = ('plan', 'created_at')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    구독을 손으로 볼 자리.

    지금까지 등록되어 있지 않아서, 알림을 받고 partner 로 바꾸거나 기간을
    미루려면 shell 을 열어야 했다.
    """
    list_display = ('restaurant', 'status', 'plan', 'current_period_end', 'photo_import_count')
    list_filter = ('status', 'plan')
    search_fields = ('restaurant__name', 'restaurant__slug')
    autocomplete_fields = ('restaurant',)


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    """
    통장과 대조하는 자리.

    확인 액션이 넷이지만 하는 일은 기간만 다르고 같다. 기간 입력 페이지를
    따로 거치게 하면 통장을 대조하다 말고 화면을 하나 더 넘겨야 해서,
    목록에서 바로 끝나게 했다.
    """
    list_display = ('created_at', 'restaurant', 'depositor_name', 'amount', 'plan', 'status')
    list_filter = ('status', 'plan')
    search_fields = ('depositor_name', 'restaurant__name', 'restaurant__slug')
    readonly_fields = ('created_at', 'confirmed_at', 'confirmed_by')
    autocomplete_fields = ('restaurant',)
    actions = ('confirm_1', 'confirm_3', 'confirm_6', 'confirm_12')

    def _confirm(self, request, queryset, months):
        opened = 0
        for payment_request in queryset:
            payment_request.confirm(months=months, user=request.user)
            opened += 1
        self.message_user(request, f'{opened}건을 {months}개월로 확인했습니다.')

    @admin.action(description='입금 확인 · 1개월')
    def confirm_1(self, request, queryset):
        self._confirm(request, queryset, 1)

    @admin.action(description='입금 확인 · 3개월')
    def confirm_3(self, request, queryset):
        self._confirm(request, queryset, 3)

    @admin.action(description='입금 확인 · 6개월')
    def confirm_6(self, request, queryset):
        self._confirm(request, queryset, 6)

    @admin.action(description='입금 확인 · 1년')
    def confirm_12(self, request, queryset):
        self._confirm(request, queryset, 12)
