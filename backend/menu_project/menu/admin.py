from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
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
    list_display = ('name', 'restaurant', 'priority')
    list_filter = ('restaurant',) # Superuser에게만 보임 (Mixin 처리)

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


@admin.register(MenuItem)
class MenuItemAdmin(RestaurantFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'price', 'display_mode', 'is_available')
    list_filter = ('restaurant', ('category', RestaurantCategoryFilter), 'is_available', 'display_mode')
    search_fields = ('name', 'description')
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

