# seed_sorok.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'menu_project.settings')
django.setup()

from menu.models import Restaurant, Category, MenuItem

def seed():
    # 1. Create or Clean Restaurant "한식술집 소록"
    slug = "sorok"
    restaurant, created = Restaurant.objects.get_or_create(
        slug=slug,
        defaults={"name": "한식술집 소록"}
    )
    if not created:
        print(f"Restaurant {restaurant.name} already exists. Cleaning existing categories and items...")
        Category.objects.filter(restaurant=restaurant).delete()
        MenuItem.objects.filter(restaurant=restaurant).delete()
    else:
        print(f"Created restaurant: {restaurant.name}")

    # 2. Create Top Categories
    cat_big = Category.objects.create(
        restaurant=restaurant,
        name="큰상",
        name_en="Main Dishes",
        priority=1.0
    )
    cat_small = Category.objects.create(
        restaurant=restaurant,
        name="작은상",
        name_en="Side Dishes & Desserts",
        priority=2.0
    )
    cat_drinks = Category.objects.create(
        restaurant=restaurant,
        name="주류",
        name_en="Drinks",
        priority=3.0
    )

    # 3. Create Sub Categories under Drinks (parent=cat_drinks)
    sub_takju = Category.objects.create(
        restaurant=restaurant,
        name="탁주 (막걸리)",
        name_en="Takju (Makgeolli)",
        parent=cat_drinks,
        priority=1.0
    )
    sub_distilled = Category.objects.create(
        restaurant=restaurant,
        name="증류주",
        name_en="Distilled Liquors",
        parent=cat_drinks,
        priority=2.0
    )
    sub_cheongju = Category.objects.create(
        restaurant=restaurant,
        name="청주 & 약주",
        name_en="Cheongju & Yakju",
        parent=cat_drinks,
        priority=3.0
    )
    sub_fruit = Category.objects.create(
        restaurant=restaurant,
        name="과실주 & 와인 & 사이더",
        name_en="Fruit Wine & Cider",
        parent=cat_drinks,
        priority=4.0
    )
    sub_highball = Category.objects.create(
        restaurant=restaurant,
        name="하이볼",
        name_en="Highballs",
        parent=cat_drinks,
        priority=5.0
    )
    sub_beersoju = Category.objects.create(
        restaurant=restaurant,
        name="맥주 & 일반소주",
        name_en="Beer & Soju",
        parent=cat_drinks,
        priority=6.0
    )
    sub_mixers = Category.objects.create(
        restaurant=restaurant,
        name="음료 & 기타 토닉",
        name_en="Beverages & Mixers",
        parent=cat_drinks,
        priority=7.0
    )

    # Helper function to bulk create MenuItems
    def add_item(cat, name, price, desc="", notes="", name_en="", priority=0.0, image_name=""):
        MenuItem.objects.create(
            restaurant=restaurant,
            category=cat,
            name=name,
            name_en=name_en,
            price=price,
            description=desc,
            notes=notes,
            priority=priority,
            menu_image=f"menu_images/{image_name}" if image_name else "",
            display_mode='combined' if image_name else 'auto',
            click_expand=False,
            enable_detail_view=bool(image_name)
        )

    # --- 큰상 Items ---
    big_items = [
        ("제철 특대 부시리 회 술상", "40,0", "10kg 급 제철 부시리 회와 밥, 목포산 곱창김, 소록표 막장, 묵은지 무침과 싸먹는 든든한 술상", "", "Seasonal Yellowtail Sashimi Table", "부시리한상.jpeg"),
        ("1++ 한우 육회와 감태김밥", "30,0", "1++ 한우를 썰어 간장양념에 버무려 감태김밥과 소록 표 특제양념과 곁들여 먹는 육회 한상", "감태김밥 추가 5,0", "Hanwoo Beef Tartare & Rice Roll", "감태육회.jpeg"),
        ("1++ 한우 육사시미 한판", "30,0", "1++ 한우를 얇게 썰어 방앗간 참기름, 소록 표 고추장다데기, 특제소스와 함께 먹는 육사시미 한판", "고노와다 추가 5,0 / 감태김밥 추가 5,0", "Hanwoo Beef Sashimi Plate", "육사시미.jpeg"),
        ("항정수육과 고흥 갓김치", "29,0", "물을 넣지 않고 야채와 과일의 수분으로 삶아내어 더욱 촉촉하고 부드러운 항정살 수육", "", "Pork Neck Suyuk & Kimchi", "항정수육.jpeg"),
        ("꽃추장찌개", "27,0", "고추장 베이스 찌개에 꽃게를 넣어 끓여낸 전라도식 고추장찌개, [기본칼국수사리 제공]", "", "Flower Gochujang Stew", ""),
        ("칼칼, 얼큰 조개뚝배기", "26,0", "바지락, 백합, 꽃게, 새우를 넣고 칼칼하게 푹 끓인 후 봄나물과 함께 먹는 빨간 조개탕", "칼국수사리 추가 3,0", "Spicy Clam Hot Pot", "조개뚝배기.jpeg"),
        ("항정살 튀김과 쌈장페스토", "24,0", "항정살을 깍둑썰어 튀김옷을 입혀 튀겨낸 후 고추마늘이 들어간 쌈장페스토와 함께먹는 일품안주", "", "Crispy Pork Neck & Ssamjang Pesto", "항정살튀김.jpeg"),
        ("조개듬뿍, 버터 술찜", "23,0", "백합조개, 바지락을 불 맛나게 볶아 청주에 쪄 먹는 조개 찜", "카펠리니 파스타 추가 3,0", "Clam Butter Wine Stew", "조개버터술찜.jpeg"),
        ("통 꽃게, 홍게장 크림파스타", "19,0", "꽃게 한 마리와 생크림에 홍게의 딱지 장을 넣어 감칠맛을 살린 소록의 시그니처 크림파스타", "", "Whole Crab & Paste Cream Pasta", "게내장크림파스타.jpeg"),
        ("우삼겹 된장술밥", "15,0", "고소한 우삼겹과 야채를 같이 볶아 낸 후 소록의 된장으로 깊은 맛을 낸 된장 술밥", "요청시 공깃밥 따로 제공", "Beef Short Plate Doenjang Rice Stew", "된장술밥.jpeg"),
    ]
    for idx, item in enumerate(big_items):
        add_item(cat_big, item[0], item[1], item[2], item[3], item[4], priority=float(idx), image_name=item[5])

    # --- 작은상 Items ---
    small_items = [
        ("감태김밥과 젓갈 3종", "15,0", "바다향이 살아있는 생감태로 말은 꼬마김밥과 씨앗젓갈, 낙지젓, 명란젓 3종 그리고 큐피마요네즈", "", "Gamtae Rice Roll & 3 Salted Seafood", "감태김밥.jpeg"),
        ("우엉튀김과 수제 할라피뇨잼마요", "13,0", "향긋한 우엉을 얇게 저며 튀겨내어, 매콤달콤한 할라피뇨잼과 큐피마요네즈를 곁들여 먹는 튀김요리", "", "Burdock Fry & Jalapeno Mayo", "우엉튀김.jpeg"),
        ("들기름 메밀국수", "12,0", "방앗간에서 짜온 들기름과 소록의 비법 맛간장을 비벼 만든 들기름메밀국수", "", "Perilla Oil Buckwheat Noodles", ""),
        ("들기름 비빔메밀국수", "12,0", "방앗간에서 짜온 들기름과 매콤달콤한 비빔양념을 넣어 간장과는 다른 스타일의 메밀국수", "", "Perilla Oil Spicy Buckwheat Noodles", "들기름메밀비빔국수.jpeg"),
        ("김치메밀전병 튀김과 부추무침", "9,5", "고기와 김치 속을 쫄깃한 메밀피로 감싼 전병을 튀겨 부추무침과 곁들여 먹는 간단 안주", "", "Kimchi Buckwheat Pancake Fry", ""),
        ("낙지젓 볶음밥", "9,5", "고슬고슬한 밥에 낙지젓을 넣어 짭짤하게 볶아 낸 밥", "", "Octopus Salted Gut Fried Rice", ""),
        ("홍시 치즈케이크", "9,0", "치즈케이크 위에 홍시퓨레를 얹어 만든 달콤한 디저트", "", "Ripe Persimmon Cheesecake", ""),
        ("게 딱지장 라면", "8,5", "녹진한 게 딱지장을 넣어 함께 먹는 해장라면", "", "Crab Paste Ramen", ""),
        ("막포카토", "7,0", "달달한 바닐라 아이스크림 위에 꿀, 견과류, 과자를 뿌려 막걸리 한잔을 부어먹는 술-저트", "", "Makpocato", ""),
        ("공기밥", "2,0", "공기밥", "", "Steamed Rice", ""),
    ]
    for idx, item in enumerate(small_items):
        add_item(cat_small, item[0], item[1], item[2], item[3], item[4], priority=float(idx), image_name=item[5])

    # --- 주류 - 탁주 Items ---
    takju_items = [
        ("호랑이 생막걸리 (750ml / 6%)", "6,0", "무 아스파탐, 자연의 당으로 발효되는 탁주, 적당한 단맛과 산미가 어우러져 기본에 충실한 탁주", "", "Tiger Raw Makgeolli"),
        ("대대포 블루 (600ml / 6%)", "9,5", "인공감미료를 첨가하지 않고 국내산 벌꿀과 천연감미료를 통해 은은하며 자연스러운 단맛을 표현하는 담양 막걸리", "숙취 예방에 도움을 주는 프리미엄 탁주", "Daedaepo Blue Makgeolli"),
        ("까만토끼 (375ml / 9%)", "19,0", "용인 백옥쌀과 국내산 흑미를 사용해 만든 프리미엄 탁주, 은은한 계피향이 어우러지는 녹진함이 일품", "", "Black Rabbit Takju"),
        ("붉은원숭이 (375ml / 10.8%)", "19,0", "선명한 붉은 빛 뒤에 따라오는 은은한 단 맛과 묵직한 바디감이 자색고구마를 연상케 하는 로제 막걸리", "", "Red Monkey Takju"),
    ]
    for idx, item in enumerate(takju_items):
        add_item(sub_takju, item[0], item[1], item[2], item[3], item[4], priority=float(idx))

    # --- 주류 - 증류주 Items ---
    distilled_items = [
        ("동해소주 (375ml / 17.5%)", "6,5", "음식의 간이 약한 강원도를 표현하듯이, 깔끔하면서 부드러움을 느끼게 해주는 강원도 소주", "", "Donghae Soju"),
        ("느린마을 증류주 (375ml / 17%)", "6,5", "전라북도 고창의 쌀을 증류한 소주원액을 최적의 비율로 블렌딩하여 만든 깔끔한 소주", "", "Neurinmaeul Distilled"),
        ("밀담 (375ml / 17%)", "8,0", "토종 단수수를 3번 증류하여 만든 국내산 럼, 깔끔한 밑의 단맛으로 시작해 잔향이 좋은 단수수 전통주", "", "Mildam"),
        ("막시모 (375ml / 17%)", "14,0", "단수수를 3번 증류한 후 오미자씨와 백자 항아리에서 숙성 시킨 향이 좋은 오미자 증류주", "", "Maximo"),
        ("가평소주 (375ml / 25%)", "15,0", "가평에서 생산되는 친환경 쌀을 감압식 증류를 통해 불쾌취를 없애, 부드러운 풍미를 자랑하는 증류주", "", "Gapyeong Soju"),
        ("애플스피릿 (375ml / 20%)", "17,0", "은은한 사과 향을 느낄 수 있는 사과증류주, 술 잘 만들기로 소문난 댄싱사이더 사의 증류주 신작", "", "Apple Spirit"),
        ("서울의 밤 (375ml / 25%)", "16,0", "높지 않은 단맛이 술의 풍미를 높혀주고 입 안을 깔끔하게 넘겨주는 매실 리큐르", "", "Seoul Night"),
        ("두레앙 (375ml / 22%)", "16,0", "'큰 봉우리'라는 뜻을 가진 거봉을 이용해 만든 큰 향과 맛이 담겨있는 거봉증류주로 은은한 포도향이 느껴짐", "", "Dureang"),
        ("황금보리 (375ml / 17%)", "18,0", "깔끔한 보리향이 느껴지는 가벼운 소주, 밸런스가 좋아 어느 한식과도 어울리는 증류주", "", "Golden Barley"),
        ("느린마을 소주 (375ml / 21%)", "19,0", "인공감미료를 첨가하지 않아 깔끔하고 담백한 맛을 표현하며 내일을 지켜주는 증류주", "", "Neurinmaeul Soju"),
        ("서울 고량주 레드 (375ml / 35%)", "25,0", "싱그러운 과일과 향긋한 꽃내음이 풍겨오는 고량주, 중국술이 아닌 한국전통주 피니쉬로 강력추천", "", "Seoul Kaoliang Red"),
        ("화요 (375ml / 25%)", "28,0", "깔끔한 스타트로 시작해 부드러움을 남기며 넘어가는 프리미엄 쌀 100% 증류주", "", "Hwayo 25"),
        ("여유소주 25 (375ml / 25%)", "28,0", "부드러운 쌀의 단맛, 고소한 맛이 어우러져 입 속에 쌀 향을 남기고 넘어가는 깔끔한 증류주", "", "Yeoyu Soju 25"),
        ("문경바람 오크 (375ml / 25%)", "33,0", "풍부한 사과 향과 오크의 스모키향을 동시에 표현하는 프리미엄 브랜디방식의 전통주", "", "Mungyeong Baram Oak 25"),
        ("가무치 (375ml / 25%)", "36,0", "100% 충청 미곡처리장의 햅쌀만을 이용해 만든 깔끔한 쌀 증류식 소주", "", "Gamuchi 25"),
        ("오크스피릿 (375ml / 35%)", "38,0", "사과 증류원액을 그대로 오크통 숙성한 한국식 깔바도스. 위스키 및 고도수를 좋아하신다면 강력추천", "", "Oak Spirit"),
        ("사락 (375ml / 33%)", "40,0", "100% 국내산 보리를 주 재료로 증류하여 오크통에 숙성한 증류주", "", "Sarak"),
        ("담솔 (375ml / 40%)", "50,0", "솔잎과 솔 순을 주 재료로 하여 깔끔하고 시원한 맛을 내는 술 증류주", "", "Damsol 40"),
        ("문경바람 오크 (375ml / 40%)", "50,0", "풍부한 사과 향과 오크의 스모키향을 동시에 표현하는 프리미엄 브랜디방식의 전통주", "", "Mungyeong Baram Oak 40"),
        ("추사 오크 40 (500ml / 40%)", "130,0", "맛과 향이 뛰어난 예산사과를 증류하여 오크통 숙성한 사과증류주 aka. 한국의 깔바도스", "", "Chusa Oak 40"),
    ]
    for idx, item in enumerate(distilled_items):
        add_item(sub_distilled, item[0], item[1], item[2], item[3], item[4], priority=float(idx))

    # --- 주류 - 청주 & 약주 Items ---
    cheongju_items = [
        ("지리산강쇠 (375ml / 13%)", "9,0", "누룩과 오미자, 산수유, 오가피 야관문 등을 넣어 만든 지리산 약주로 어느 한식과도 잘 어울리는 편", "", "Jirisan Gangsoe"),
        ("마산정종 (500ml / 14%)", "22,0", "경남 창원의 양조장에서 탄생해 생선 회, 육사시미 등 날 것과 페어링이 좋은 사케st 정종", "", "Masan Jungjong"),
        ("부산청주 (500ml / 14%)", "24,0", "부산의 쌀을 이용하여 빚은 청주로 적당한 바디감에 목넘김이 좋은 술", "", "Busan Cheongju"),
        ("고흥 유자주 (8% / 500ml)", "24,0", "100% 고흥 유자와 쌀로 만든 유자 약주, 8% 버전", "", "Goheung Yuza Wine 8%"),
        ("고흥 유자주 (12% / 500ml)", "27,0", "100% 고흥 유자와 쌀로 만든 유자 약주, 12% 버전", "", "Goheung Yuza Wine 12%"),
        ("서설(청주) (375ml / 13%)", "28,0", "첫 눈이 내렸을 때, 아무도 밟지 않은 거리의 눈처럼 깨끗한 맛을 연상시키는 담백하고 부드러운 청주", "", "Seoseol"),
        ("우렁이쌀 청주 (500ml / 14%)", "41,0", "우렁이 농법으로 재배한 무농약 논산 찹쌀로 빚어 감미료를 따로 첨가하지 않고 숙성한 프리미엄 청주", "", "Urongisal Cheongju"),
    ]
    for idx, item in enumerate(cheongju_items):
        add_item(sub_cheongju, item[0], item[1], item[2], item[3], item[4], priority=float(idx))

    # --- 주류 - 과실주 Items ---
    fruit_items = [
        ("에피소드 상그리아 (275ml / 3%)", "8,0", "낮은 도수로 상그리아 맛을 느낄 수 있는 스파클링 와인으로 식전주로 추천", "", "Episode Sangria"),
        ("호감 (330ml / 6%)", "10,0", "단감을 사랑한 호랑이, 적당한 탄산과 은은한 감의 단맛이 느껴지는 스파클링 과실주", "", "Hogam"),
        ("장수 오미자주 (375ml / 16%)", "13,0", "오미자의 맛을 그대로 술로 표현한 맛, 산미와 단맛 밸런스가 좋아 부담 없이 마시기 좋은 술", "", "Jangsu Omija Wine"),
        ("매실원주 (375ml / 13%)", "14,0", "매실주 원액 100%와 제주도 꿀이 첨가된 매실주로 높은 당도로 시작하기에 좋은 술", "", "Maesil Wonju"),
        ("심플리아플 (350ml / 12%)", "16,0", "천연 사과즙의 상큼함이 입안 가득 퍼지는 깔끔한 사과주로 은은한 단맛의 피니쉬가 있는 술", "", "Simply Apple"),
        ("술샘 (375ml / 16%)", "25,0", "다섯가지의 맛을 표현한다는 오미자를 술로 만든, 풍미가 깊은 리큐르", "", "Soolsaem"),
        ("꿀샘 (375ml / 16%)", "25,0", "100% 천연벌꿀 벌꿀주에 생강을 추출해 넣어 깔끔함과 벌꿀이 어우러지는 리큐르", "", "Kkulsaem"),
        ("애플로제 (750ml / 6.4%)", "27,0", "오미자, 라즈베리, 사과가 블렌딩 되어 라즈베리의 달짝지근한 향과 새콤한 맛이 나는 스파클링 와인", "", "Apple Rose"),
        ("댄싱파파 (750ml / 4.9%)", "27,0", "사과를 착즙해서 만든 발효주로 사과, 배, 꿀의 조화로운 풍미가 느껴지는 스파클링 와인", "", "Dancing Papa"),
        ("요린넨 사이더 (750ml / 4.7%)", "28,0", "사과의 상큼함과 자몽의 새콤함, 우수한 밸런스와 바질 향이 피니시를 잡아주는 깔끔한 스파클링 와인", "", "Yolinnen Cider"),
    ]
    for idx, item in enumerate(fruit_items):
        add_item(sub_fruit, item[0], item[1], item[2], item[3], item[4], priority=float(idx))

    # --- 주류 - 하이볼 Items ---
    highball_items = [
        ("문경바람 하이볼", "7,9", "문경바람 위스키 전통주를 베이스로 만든 하이볼", "", "Mungyeong Baram Highball"),
        ("복분자 하이볼", "7,9", "만월 복분자주와 복분자원액을 블렌딩해 만든 달콤한 복분자 하이볼", "", "Bokbunja Highball"),
        ("유자민트 하이볼 (논알콜 가능)", "7,9", "유자민트 시럽과 보드카로 만든 소록만의 달달한 하이볼", "", "Yuza Mint Highball"),
        ("매실 하이볼", "7,9", "서울의 밤 40도를 베이스로 매실액기스와 블렌딩해 어린 시절 먹던 추억의 맛을 표현한 매실 하이볼", "", "Maesil Highball"),
    ]
    for idx, item in enumerate(highball_items):
        add_item(sub_highball, item[0], item[1], item[2], item[3], item[4], priority=float(idx))

    # --- 주류 - 맥주 & 일반소주 Items ---
    beer_items = [
        ("아사히 生 드래프트", "8,9", "사장님이 마시려고 넣은 아사히 생맥주", "", "Asahi Draft Beer"),
        ("소주 (진로/참이슬/처음처럼/새로)", "5,0", "대중적인 일반 소주 선택 가능", "", "Soju"),
        ("맥주 (카스/테라)", "5,0", "시원한 국산 맥주 선택 가능", "", "Korean Beer"),
        ("논알콜 칭따오 (330ml)", "5,0", "깔끔한 무알콜 맥주", "", "Non-Alcohol Tsingtao"),
    ]
    for idx, item in enumerate(beer_items):
        add_item(sub_beersoju, item[0], item[1], item[2], item[3], item[4], priority=float(idx))

    # --- 주류 - 음료 & 기타 Items ---
    mixer_items = [
        ("콜라 / 제로콜라 / 사이다", "2,0", "소프트 드링크 음료", "", "Soft Drink"),
        ("진저에일", "2,0", "진저에일 토닉", "", "Ginger Ale"),
        ("토닉워터", "3,0", "믹싱용 토닉워터", "", "Tonic Water"),
        ("레몬슬라이스", "3,0", "생 레몬 슬라이스 가니쉬", "", "Lemon Slice"),
    ]
    for idx, item in enumerate(mixer_items):
        add_item(sub_mixers, item[0], item[1], item[2], item[3], item[4], priority=float(idx))

    # 4. Create and Associate Manager User
    from django.contrib.auth.models import User
    from menu.models import UserProfile

    user, user_created = User.objects.get_or_create(username='drinkatsorok')
    user.set_password('sorok248@')
    user.is_staff = True
    user.save()
    print(f"Manager User 'drinkatsorok' created/updated (Created: {user_created})")

    profile, profile_created = UserProfile.objects.get_or_create(user=user)
    profile.restaurant = restaurant
    profile.save()
    print(f"UserProfile for 'drinkatsorok' associated with '{restaurant.name}' (Created: {profile_created})")

    print("Successfully seeded all Sorok categories, menu items, and manager user!")

if __name__ == '__main__':
    seed()
