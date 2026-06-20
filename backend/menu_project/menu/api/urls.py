from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # 레스토랑
    path('restaurants/', views.RestaurantListView.as_view(), name='restaurant-list'),
    path('restaurants/<slug:slug>/', views.RestaurantDetailView.as_view(), name='restaurant-detail'),

    # 카테고리
    path('restaurants/<slug:slug>/categories/', views.CategoryListView.as_view(), name='category-list'),
    path('restaurants/<slug:slug>/categories/<int:category_id>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('restaurants/<slug:slug>/category-tree/', views.CategoryTreeView.as_view(), name='category-tree'),

    # 검색
    path('restaurants/<slug:slug>/search/', views.SearchView.as_view(), name='search'),

    # QR 코드
    path('restaurants/<slug:slug>/qr/', views.QRCodeView.as_view(), name='qr-code'),

    # 제휴 문의
    path('contact/', views.ContactSubmitView.as_view(), name='contact-submit'),
]
