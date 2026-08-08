from django.urls import path
from . import views
from . import search_views
from . import admin_views
from . import qr_views

app_name = 'menu'

urlpatterns = [
    path('', views.menu_main, name='menu_main'),
    path('category/<int:category_id>/', views.menu_list, name='menu_list'),
    
    # API for AJAX search (will be removed from templates but kept for now)
    path('api/search/', search_views.search_api, name='search_api'),
    
    # New server-side search
    path('search/', search_views.search_redirect_view, name='search_redirect'),
    
    # QR Code
    path('qr/', qr_views.generate_qr_code, name='qr_code'),
    
    # Admin Views
    path('admin/login/', admin_views.admin_login, name='admin_login'),
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    
    path('admin/category/add/', admin_views.add_category, name='add_category'),
    path('admin/category/edit/<int:category_id>/', admin_views.edit_category, name='edit_category'),
    path('admin/category/delete/<int:category_id>/', admin_views.delete_category, name='delete_category'),
    path('admin/category/reorder/', admin_views.reorder_categories, name='reorder_categories'),
    
    path('admin/menu/add/', admin_views.add_menu, name='add_menu'),
    path('admin/menu/edit/<int:menu_id>/', admin_views.edit_menu, name='edit_menu'),
    path('admin/menu/duplicate/<int:menu_id>/', admin_views.duplicate_menu, name='duplicate_menu'),
    path('admin/menu/delete/<int:menu_id>/', admin_views.delete_menu, name='delete_menu'),
    path('admin/menu/reorder/', admin_views.reorder_menus, name='reorder_menus'),

    # 종이 메뉴판 사진 → 메뉴 자동 등록
    path('admin/menu/import/', admin_views.import_menu, name='import_menu'),
    path('admin/menu/import/commit/', admin_views.import_menu_commit, name='import_menu_commit'),

    # Real-time Order Dashboard
    path('admin/orders/', admin_views.admin_orders, name='admin_orders'),
    path('admin/orders/<int:order_id>/update-status/', admin_views.update_order_status, name='update_order_status'),
]