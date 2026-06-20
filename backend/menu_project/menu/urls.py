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
    path('admin/category/delete/<int:category_id>/', admin_views.delete_category, name='delete_category'),
    
    path('admin/menu/add/', admin_views.add_menu, name='add_menu'),
    path('admin/menu/edit/<int:menu_id>/', admin_views.edit_menu, name='edit_menu'),
    path('admin/menu/delete/<int:menu_id>/', admin_views.delete_menu, name='delete_menu'),
]