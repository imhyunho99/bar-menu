import requests
import logging
from .models import SiteSettings

logger = logging.getLogger(__name__)

def send_order_to_payhere(order):
    """
    고객 주문을 매장의 페이히어(Payhere) POS 기기로 실시간 동기화/전송합니다.
    (후불 테이블 오더 전송 지원)
    """
    settings = SiteSettings.objects.filter(restaurant=order.restaurant).first()
    if not settings:
        logger.info(f"SiteSettings not found for restaurant {order.restaurant.name}")
        return False
        
    if not settings.enable_payhere:
        logger.info(f"Payhere integration disabled for restaurant {order.restaurant.name}")
        return False

    if not settings.payhere_api_key:
        logger.warn(f"Payhere API key is missing for restaurant {order.restaurant.name}. Order cannot be sent to POS.")
        return False

    # HTTP 요청 헤더 구성
    headers = {
        "Authorization": f"Bearer {settings.payhere_api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 주문 상품 항목 리스트 구성
    order_items = []
    for item in order.items.all():
        order_items.append({
            "name": item.name,
            "price": int(item.price),
            "quantity": int(item.quantity)
        })

    # Payhere 주문 등록 표준 페이로드
    payload = {
        "orderType": "TABLE",
        "tableName": order.table_number,
        "items": order_items,
        "totalAmount": order.total_price,
        "metadata": {
            "source": "bar-menu QR Order System",
            "orderId": order.id
        }
    }

    # 페이히어 POS API 엔드포인트
    shop_id = settings.payhere_store_id or "default"
    endpoint = f"https://api.payhere.in/v1/shops/{shop_id}/orders"

    logger.info(f"[Payhere API] Sending Order #{order.id} to POS. Endpoint: {endpoint}")
    logger.info(f"[Payhere API] Payload: {payload}")

    try:
        # 5초 타임아웃으로 POST 요청 전송
        response = requests.post(endpoint, json=payload, headers=headers, timeout=5)
        
        logger.info(f"[Payhere API] Response Status Code: {response.status_code}")
        logger.info(f"[Payhere API] Response Body: {response.text}")
        
        if response.status_code in [200, 201]:
            logger.info(f"[Payhere API] Order #{order.id} registered in Payhere POS successfully.")
            return True
        else:
            logger.error(f"[Payhere API] POS registration failed with status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"[Payhere API] Network error connecting to Payhere API: {e}")
        return False
