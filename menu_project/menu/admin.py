from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Restaurant, UserProfile, Category, MenuItem, SiteSettings

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

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            # 일반 유저에게는 restaurant 필드를 숨김 (자동 할당되므로)
            if 'restaurant' in form.base_fields:
                del form.base_fields['restaurant']
        return form

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

@admin.register(MenuItem)
class MenuItemAdmin(RestaurantFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'price', 'is_available')
    list_filter = ('restaurant', 'category', 'is_available')
    search_fields = ('name', 'description')
    
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
            'fields': ('restaurant', 'logo_image', 'intro_image', 'intro_video', 'side_image')
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
    )
    
    def has_add_permission(self, request):
        # 이미 설정이 있다면 추가 불가능하게 (1:1 관계처럼 유지)
        if not request.user.is_superuser:
            if hasattr(request.user, 'profile') and request.user.profile.restaurant:
                if SiteSettings.objects.filter(restaurant=request.user.profile.restaurant).exists():
                    return False
        return super().has_add_permission(request)
