from rest_framework import serializers
from ..models import Restaurant, SiteSettings, Category, MenuItem, MenuItemPairing, ContactSubmission, Order, OrderItem


class MenuItemPairingSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = MenuItemPairing
        fields = ['id', 'name', 'image', 'description', 'price', 'priority']

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class MenuItemSerializer(serializers.ModelSerializer):
    pairings = MenuItemPairingSerializer(many=True, read_only=True)
    menu_image = serializers.SerializerMethodField()
    detail_image = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'name_en', 'price', 'description', 'notes',
            'menu_image', 'detail_image', 'priority', 'is_available',
            'display_mode', 'click_expand', 'lightbox_style', 'lightbox_opacity',
            'enable_detail_view', 'detail_description',
            'pairings',
        ]

    def _build_media_url(self, image_field):
        if image_field:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(image_field.url)
            return image_field.url
        return None

    def get_menu_image(self, obj):
        return self._build_media_url(obj.menu_image)

    def get_detail_image(self, obj):
        return self._build_media_url(obj.detail_image)


class CategorySerializer(serializers.ModelSerializer):
    category_image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'name_en', 'priority', 'parent',
            'category_image', 'hide_side_image',
        ]

    def get_category_image(self, obj):
        if obj.category_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.category_image.url)
            return obj.category_image.url
        return None


class CategoryDetailSerializer(CategorySerializer):
    """카테고리 상세 — 하위 카테고리 목록 포함"""
    sub_categories = CategorySerializer(many=True, read_only=True)
    menu_items = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + ['sub_categories', 'menu_items']

    def get_menu_items(self, obj):
        """
        최하위 카테고리일 때만 메뉴 아이템 반환.

        페어링을 같이 끌어온다. 안 걸면 메뉴마다 한 번씩 나가서, 메뉴 121개
        짜리 카테고리에서 쿼리가 114번이었다 — 손님이 카테고리를 누를 때마다
        도는 경로라 메뉴가 많은 가게일수록 그대로 느려진다.
        """
        if not obj.sub_categories.exists():
            items = MenuItem.objects.filter(
                category=obj,
                is_available=True,
                restaurant=obj.restaurant
            ).prefetch_related('pairings').order_by('priority', 'name')
            return MenuItemSerializer(items, many=True, context=self.context).data
        return []


class CategoryTreeSerializer(serializers.ModelSerializer):
    """사이드 메뉴용 — 전체 카테고리 트리"""
    sub_categories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'name_en', 'priority', 'parent', 'category_image', 'hide_side_image', 'sub_categories']

    def get_sub_categories(self, obj):
        """
        자식 카테고리. 미리 받아 둔 묶음이 있으면 그걸 쓴다.

        예전에는 여기서 obj.sub_categories.all().order_by(...) 를 불렀다.
        .order_by() 는 prefetch 캐시를 버리기 때문에 카테고리마다 쿼리가
        한 번씩 나갔다 — 24개짜리 매장에서 29번. 코드만 봐서는 prefetch 가
        걸려 있으니 괜찮아 보이는 게 이 함정의 고약한 점이다.

        children_by_parent 가 없을 때의 폴백은 남겨 둔다. 느리지만 틀리지는
        않는다 — 이 직렬화기를 다른 곳에서 쓰게 되는 날 조용히 비는 것보다 낫다.
        """
        children_by_parent = self.context.get('children_by_parent')
        if children_by_parent is None:
            children = obj.sub_categories.all().order_by('priority', 'name')
        else:
            children = children_by_parent.get(obj.id, [])
        return CategoryTreeSerializer(children, many=True, context=self.context).data


class SiteSettingsSerializer(serializers.ModelSerializer):
    """사이트 설정 전체 — 동적 스타일링에 사용"""
    logo_image = serializers.SerializerMethodField()
    intro_image = serializers.SerializerMethodField()
    intro_video = serializers.SerializerMethodField()
    loading_video_2 = serializers.SerializerMethodField()
    side_image = serializers.SerializerMethodField()

    # 폰트 파일 URL들
    menu_name_font_url = serializers.SerializerMethodField()
    menu_name_en_font_url = serializers.SerializerMethodField()
    menu_price_font_url = serializers.SerializerMethodField()
    menu_description_font_url = serializers.SerializerMethodField()
    menu_notes_font_url = serializers.SerializerMethodField()
    category_name_font_url = serializers.SerializerMethodField()
    category_name_en_font_url = serializers.SerializerMethodField()
    pairing_name_font_url = serializers.SerializerMethodField()
    pairing_description_font_url = serializers.SerializerMethodField()
    pairing_price_font_url = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = [
            'logo_image', 'intro_image', 'intro_video', 'loading_video_2',
            'show_manual_card', 'side_image',
            'category_card_layout_json', 'menu_card_layout_json',
            'background_color', 'category_card_color', 'menu_card_color',
            'wifi_ssid', 'wifi_password', 'wifi_security', 'enable_wifi', 'enable_payhere', 'enable_cart', 'payhere_store_id', 'restrict_by_ip', 'store_public_ip', 'restrict_by_wifi_ssid', 'disable_screenshots',
            # 메뉴명(한글)
            'menu_name_font_url', 'menu_name_color', 'menu_name_size',
            'menu_name_bold', 'menu_name_italic',
            # 메뉴명(영문)
            'menu_name_en_font_url', 'menu_name_en_color', 'menu_name_en_size',
            'menu_name_en_bold', 'menu_name_en_italic',
            # 가격
            'menu_price_font_url', 'menu_price_color', 'menu_price_size',
            'menu_price_bold', 'menu_price_italic',
            # 메뉴 설명
            'menu_description_font_url', 'menu_description_color', 'menu_description_size',
            'menu_description_bold', 'menu_description_italic',
            # 기타 사항
            'menu_notes_font_url', 'menu_notes_color', 'menu_notes_size',
            'menu_notes_bold', 'menu_notes_italic',
            # 카테고리명(한글)
            'category_name_font_url', 'category_name_color', 'category_name_size',
            'category_name_bold', 'category_name_italic',
            # 카테고리명(영문)
            'category_name_en_font_url', 'category_name_en_color', 'category_name_en_size',
            'category_name_en_bold', 'category_name_en_italic',
            # 페어링명
            'pairing_name_font_url', 'pairing_name_color', 'pairing_name_size',
            'pairing_name_bold', 'pairing_name_italic',
            # 페어링 설명
            'pairing_description_font_url', 'pairing_description_color', 'pairing_description_size',
            'pairing_description_bold', 'pairing_description_italic',
            # 페어링 가격
            'pairing_price_font_url', 'pairing_price_color', 'pairing_price_size',
            'pairing_price_bold', 'pairing_price_italic',
        ]

    def _build_media_url(self, file_field):
        if file_field and file_field.name:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(file_field.url)
            return file_field.url
        return None

    # 미디어 파일 URL 메서드들
    def get_logo_image(self, obj):
        return self._build_media_url(obj.logo_image)

    def get_intro_image(self, obj):
        return self._build_media_url(obj.intro_image)

    def get_intro_video(self, obj):
        return self._build_media_url(obj.intro_video)

    def get_loading_video_2(self, obj):
        return self._build_media_url(obj.loading_video_2)

    def get_side_image(self, obj):
        return self._build_media_url(obj.side_image)

    # 폰트 파일 URL 메서드들
    def get_menu_name_font_url(self, obj):
        return self._build_media_url(obj.menu_name_font)

    def get_menu_name_en_font_url(self, obj):
        return self._build_media_url(obj.menu_name_en_font)

    def get_menu_price_font_url(self, obj):
        return self._build_media_url(obj.menu_price_font)

    def get_menu_description_font_url(self, obj):
        return self._build_media_url(obj.menu_description_font)

    def get_menu_notes_font_url(self, obj):
        return self._build_media_url(obj.menu_notes_font)

    def get_category_name_font_url(self, obj):
        return self._build_media_url(obj.category_name_font)

    def get_category_name_en_font_url(self, obj):
        return self._build_media_url(obj.category_name_en_font)

    def get_pairing_name_font_url(self, obj):
        return self._build_media_url(obj.pairing_name_font)

    def get_pairing_description_font_url(self, obj):
        return self._build_media_url(obj.pairing_description_font)

    def get_pairing_price_font_url(self, obj):
        return self._build_media_url(obj.pairing_price_font)


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'slug']


class RestaurantDetailSerializer(RestaurantSerializer):
    """레스토랑 상세 — SiteSettings 포함"""
    site_settings = serializers.SerializerMethodField()
    menu_is_live = serializers.SerializerMethodField()

    class Meta(RestaurantSerializer.Meta):
        fields = RestaurantSerializer.Meta.fields + ['site_settings', 'menu_is_live']

    def get_menu_is_live(self, obj):
        """
        손님에게 실제로 열려 있는가.

        미리보기 워터마크가 이걸 본다. 토큰이 있느냐만 보면, 결제하고 열린
        뒤에도 쿠키에 남은 토큰 때문에 최대 하루 동안 자기 영업 중인
        메뉴판에서 '손님에게는 보이지 않습니다' 를 읽게 된다.
        """
        subscription = getattr(obj, 'subscription', None)
        return bool(subscription and subscription.menu_is_live())

    def get_site_settings(self, obj):
        settings = SiteSettings.objects.filter(restaurant=obj).first()
        if settings:
            return SiteSettingsSerializer(settings, context=self.context).data
        return None


class ContactSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = ['name', 'contact_info', 'plan']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['menu_item', 'name', 'price', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'table_number', 'status', 'total_price', 'created_at', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order
