import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import CircleModuleDrawer
from PIL import Image, ImageDraw
from io import BytesIO
import base64

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.shortcuts import get_object_or_404

from ..models import Restaurant, SiteSettings, Category, MenuItem
from .serializers import (
    RestaurantSerializer,
    RestaurantDetailSerializer,
    CategorySerializer,
    CategoryDetailSerializer,
    CategoryTreeSerializer,
    MenuItemSerializer,
    ContactSubmissionSerializer,
    OrderSerializer,
)


class RestaurantListView(APIView):
    """GET /api/v1/restaurants/ — 전체 레스토랑 목록"""

    def get(self, request):
        restaurants = Restaurant.objects.all().order_by('name')
        serializer = RestaurantSerializer(restaurants, many=True, context={'request': request})
        return Response(serializer.data)


class RestaurantDetailView(APIView):
    """GET /api/v1/restaurants/<slug>/ — 레스토랑 상세 (SiteSettings 포함)"""

    def get(self, request, slug):
        restaurant = get_object_or_404(Restaurant, slug=slug)
        serializer = RestaurantDetailSerializer(restaurant, context={'request': request})
        return Response(serializer.data)


class CategoryListView(APIView):
    """GET /api/v1/restaurants/<slug>/categories/ — 최상위 카테고리 목록"""

    def get(self, request, slug):
        restaurant = get_object_or_404(Restaurant, slug=slug)
        categories = Category.objects.filter(
            parent=None,
            restaurant=restaurant
        ).distinct().order_by('priority', 'name')
        serializer = CategorySerializer(categories, many=True, context={'request': request})
        return Response(serializer.data)


class CategoryDetailView(APIView):
    """GET /api/v1/restaurants/<slug>/categories/<id>/ — 카테고리 상세 (하위 카테고리 or 메뉴 아이템)"""

    def get(self, request, slug, category_id):
        restaurant = get_object_or_404(Restaurant, slug=slug)
        category = get_object_or_404(
            Category.objects.prefetch_related('sub_categories'),
            id=category_id,
            restaurant=restaurant
        )
        serializer = CategoryDetailSerializer(category, context={'request': request})

        # 순환 네비게이션 정보 추가 (이전/다음 카테고리)
        response_data = serializer.data

        if not category.sub_categories.exists():
            all_menu_categories = Category.objects.filter(
                menu_items__is_available=True,
                restaurant=restaurant
            ).distinct().order_by('priority', 'name')
            menu_categories_list = list(all_menu_categories)

            current_index = None
            for i, cat in enumerate(menu_categories_list):
                if cat.id == category.id:
                    current_index = i
                    break

            prev_category = None
            next_category = None

            if current_index is not None and len(menu_categories_list) > 1:
                next_index = (current_index + 1) % len(menu_categories_list)
                next_category = menu_categories_list[next_index]
                prev_index = (current_index - 1 + len(menu_categories_list)) % len(menu_categories_list)
                prev_category = menu_categories_list[prev_index]

            response_data['prev_category'] = (
                {'id': prev_category.id, 'name': prev_category.name}
                if prev_category else None
            )
            response_data['next_category'] = (
                {'id': next_category.id, 'name': next_category.name}
                if next_category else None
            )

        return Response(response_data)


class CategoryTreeView(APIView):
    """GET /api/v1/restaurants/<slug>/category-tree/ — 사이드 메뉴용 전체 카테고리 트리"""

    def get(self, request, slug):
        restaurant = get_object_or_404(Restaurant, slug=slug)
        top_categories = Category.objects.filter(
            parent=None,
            restaurant=restaurant
        ).prefetch_related('sub_categories').distinct().order_by('priority', 'name')
        serializer = CategoryTreeSerializer(top_categories, many=True, context={'request': request})
        return Response(serializer.data)


class SearchView(APIView):
    """GET /api/v1/restaurants/<slug>/search/?q= — 메뉴 및 카테고리 검색"""

    def get(self, request, slug):
        restaurant = get_object_or_404(Restaurant, slug=slug)
        query = request.GET.get('q', '').strip()

        if not query or len(query) < 2:
            return Response({'results': []})

        results = []

        # 카테고리 검색
        categories = Category.objects.filter(
            Q(name__icontains=query),
            restaurant=restaurant
        ).exclude(name__icontains='인트로').distinct()[:5]

        for category in categories:
            results.append({
                'type': 'category',
                'id': category.id,
                'title': category.name,
                'subtitle': '카테고리',
            })

        # 메뉴 검색
        menu_items = MenuItem.objects.filter(
            Q(name__icontains=query) |
            Q(name_en__icontains=query) |
            Q(description__icontains=query),
            is_available=True,
            restaurant=restaurant
        ).distinct()[:5]

        for item in menu_items:
            price_raw = str(item.price)
            cleaned = price_raw.replace(',', '')
            if cleaned.replace('.', '', 1).isdigit():
                price_formatted = f"₩{price_raw}"
            else:
                price_formatted = price_raw

            results.append({
                'type': 'menu',
                'id': item.id,
                'title': item.name,
                'subtitle': f'{item.category.name if item.category else "메뉴"} - {price_formatted}',
                'category_id': item.category.id if item.category else None,
            })

        return Response({'results': results[:8]})


class QRCodeView(APIView):
    """GET /api/v1/restaurants/<slug>/qr/?base_url= — QR 코드 이미지 (base64)"""

    def get(self, request, slug):
        restaurant = get_object_or_404(Restaurant, slug=slug)

        # FE에서 base_url을 전달하거나, 요청 host 기반으로 생성
        base_url = request.GET.get('base_url', '')
        if base_url:
            menu_url = f"{base_url.rstrip('/')}/{slug}/"
        else:
            host = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
            menu_url = f"{protocol}://{host}/{slug}/"

        # 로고 이미지
        logo_img = None
        site_settings = SiteSettings.objects.filter(restaurant=restaurant).first()
        if site_settings:
            if site_settings.restrict_by_wifi_ssid and site_settings.wifi_ssid:
                import urllib.parse
                menu_url = f"{menu_url}?wifi={urllib.parse.quote(site_settings.wifi_ssid)}"
            if site_settings.logo_image:
                try:
                    logo_img = Image.open(site_settings.logo_image.path)
                except Exception:
                    logo_img = None
            # QR 코드 생성
        box_size = 10
        border = 4
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=box_size,
            border=border,
        )
        qr.add_data(menu_url)
        qr.make(fit=True)

        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=CircleModuleDrawer(),
            eye_drawer=CircleModuleDrawer(),
            embed_image=logo_img
        )

        img_pil = img.convert("RGB")
        draw = ImageDraw.Draw(img_pil)

        matrix_size = len(qr.modules)
        eye_positions = [
            (0, 0),
            (0, matrix_size - 7),
            (matrix_size - 7, 0)
        ]

        for r, c in eye_positions:
            x = (c + border) * box_size
            y = (r + border) * box_size
            width = 7 * box_size
            draw.rectangle([x, y, x + width, y + width], fill="white")
            ring_width = box_size
            draw.ellipse([x, y, x + width, y + width], outline="black", width=ring_width)
            dot_margin = 2 * box_size
            draw.ellipse([x + dot_margin, y + dot_margin, x + width - dot_margin, y + width - dot_margin], fill="black")

        buffer = BytesIO()
        img_pil.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return Response({
            'qr_image': img_str,
            'menu_url': menu_url,
        })


class ContactSubmitView(APIView):
    """POST /api/v1/contact/ — 제휴 문의 접수"""

    def post(self, request):
        serializer = ContactSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'status': 'success', 'message': '문의가 정상적으로 접수되었습니다. 확인 후 연락드리겠습니다.'},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'status': 'error', 'message': '모든 필드를 입력해 주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class OrderCreateView(APIView):
    """POST /api/v1/restaurants/<slug>/orders/ — 주문 접수"""

    def post(self, request, slug):
        restaurant = get_object_or_404(Restaurant, slug=slug)
        data = request.data.copy()
        
        # Calculate total price on backend
        total_price = 0
        items_data = data.get('items', [])
        for item in items_data:
            try:
                menu_item = MenuItem.objects.get(id=item.get('menu_item'), restaurant=restaurant)
                item['name'] = menu_item.name
                
                # Strip currency and formatting symbols, convert to numeric value
                price_str = str(menu_item.price).replace('₩', '').replace(',', '').strip()
                try:
                    price_val = int(float(price_str))
                except ValueError:
                    price_val = 0
                
                item['price'] = price_val
                quantity = int(item.get('quantity', 1))
                if quantity > 99:
                    return Response(
                        {'status': 'error', 'message': '수량은 1~99 사이여야 합니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if quantity < 1:
                    quantity = 1
                item['quantity'] = quantity
                total_price += price_val * quantity
            except MenuItem.DoesNotExist:
                return Response(
                    {'status': 'error', 'message': f"메뉴 ID {item.get('menu_item')} 존재하지 않습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        data['total_price'] = total_price
        
        serializer = OrderSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save(restaurant=restaurant)
            
            # Payhere POS 주문 전송 연동 (실제 오류가 주문 플로우에 영향을 주지 않도록 예외 처리)
            try:
                from ..payhere_api import send_order_to_payhere
                send_order_to_payhere(order)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error in send_order_to_payhere: {e}")

            return Response(
                {
                    'status': 'success',
                    'message': '주문이 성공적으로 접수되었습니다.',
                    'order_id': order.id,
                    'total_price': order.total_price
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
