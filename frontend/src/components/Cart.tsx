'use client';

import { useState, useEffect } from 'react';
import { useRestaurant } from '@/app/[restaurantSlug]/context';
import { createOrder } from '@/lib/api';
import type { MenuItem } from '@/lib/types';

interface CartItem {
  item: MenuItem;
  quantity: number;
}

export default function Cart() {
  const { restaurant } = useRestaurant();
  const slug = restaurant.slug;
  const enablePayhere = restaurant.site_settings?.enable_payhere ?? false;
  const enableCart = restaurant.site_settings?.enable_cart ?? false;

  const [cart, setCart] = useState<CartItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [tableNum, setTableNum] = useState('');
  const [isCheckoutSimulating, setIsCheckoutSimulating] = useState(false);
  const [simulationStep, setSimulationStep] = useState<'input' | 'processing' | 'success'>('input');
  const [createdOrderId, setCreatedOrderId] = useState<number | null>(null);

  // Load cart from sessionStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedCart = sessionStorage.getItem(`cart_${slug}`);
      if (savedCart) {
        try {
          setCart(JSON.parse(savedCart));
        } catch (e) {
          console.error('Failed to parse cart data', e);
        }
      }
      const savedTable = sessionStorage.getItem(`table_${slug}`);
      if (savedTable) {
        setTableNum(savedTable);
      }
    }
  }, [slug]);

  // Save cart to sessionStorage when it changes
  const saveCart = (newCart: CartItem[]) => {
    setCart(newCart);
    sessionStorage.setItem(`cart_${slug}`, JSON.stringify(newCart));
  };

  // Listen to global add-to-cart events
  useEffect(() => {
    const handleAddToCart = (e: Event) => {
      const menuItem = (e as CustomEvent).detail as MenuItem;
      setCart((prevCart) => {
        const existing = prevCart.find((c) => c.item.id === menuItem.id);
        let updated: CartItem[];
        if (existing) {
          updated = prevCart.map((c) =>
            c.item.id === menuItem.id ? { ...c, quantity: c.quantity + 1 } : c
          );
        } else {
          updated = [...prevCart, { item: menuItem, quantity: 1 }];
        }
        sessionStorage.setItem(`cart_${slug}`, JSON.stringify(updated));
        
        // Show brief cart drawer or feedback when added
        setIsOpen(true);
        return updated;
      });
    };

    window.addEventListener('add-to-cart', handleAddToCart);
    return () => {
      window.removeEventListener('add-to-cart', handleAddToCart);
    };
  }, [slug]);

  const updateQuantity = (itemId: number, delta: number) => {
    const item = cart.find((c) => c.item.id === itemId);
    if (!item) return;
    const newQty = item.quantity + delta;
    if (newQty <= 0) {
      const filtered = cart.filter((c) => c.item.id !== itemId);
      saveCart(filtered);
    } else {
      const updated = cart.map((c) =>
        c.item.id === itemId ? { ...c, quantity: newQty } : c
      );
      saveCart(updated);
    }
  };

  const clearCart = () => {
    saveCart([]);
  };

  const getCleanPrice = (priceStr: string): number => {
    const cleaned = priceStr.replace('₩', '').replace(',', '').trim();
    const val = parseInt(cleaned, 10);
    return isNaN(val) ? 0 : val;
  };

  const getTotalPrice = () => {
    return cart.reduce((acc, curr) => acc + getCleanPrice(curr.item.price) * curr.quantity, 0);
  };

  const handleOrderSubmit = async () => {
    if (!tableNum.trim()) {
      alert('테이블 번호를 입력해 주세요.');
      return;
    }
    
    // Save table number for next time
    sessionStorage.setItem(`table_${slug}`, tableNum);

    if (enablePayhere) {
      // Launch Payhere payment sheet simulator
      setIsCheckoutSimulating(true);
      setSimulationStep('input');
    } else {
      // Direct order submission
      submitDirectOrder();
    }
  };

  const submitDirectOrder = async () => {
    try {
      const itemsPayload = cart.map((c) => ({
        menu_item: c.item.id,
        quantity: c.quantity,
      }));

      const res = await createOrder(slug, {
        table_number: tableNum,
        items: itemsPayload,
      });

      if (res.status === 'success') {
        alert(`주문이 완료되었습니다! 주문 번호: #${res.order_id}`);
        clearCart();
        setIsOpen(false);
      } else {
        alert('주문 전송에 실패했습니다.');
      }
    } catch (err) {
      console.error(err);
      alert('주문 처리 중 오류가 발생했습니다.');
    }
  };

  const executeMockPayment = () => {
    setSimulationStep('processing');
    
    // Simulate PG payment delay
    setTimeout(async () => {
      try {
        const itemsPayload = cart.map((c) => ({
          menu_item: c.item.id,
          quantity: c.quantity,
        }));

        const res = await createOrder(slug, {
          table_number: tableNum,
          items: itemsPayload,
        });

        if (res.status === 'success') {
          setCreatedOrderId(res.order_id);
          setSimulationStep('success');
          clearCart();
          
          // Close after 4 seconds
          setTimeout(() => {
            setIsCheckoutSimulating(false);
            setIsOpen(false);
            setCreatedOrderId(null);
          }, 4000);
        } else {
          alert('결제 승인은 성공했으나 주문 정보 연동에 실패했습니다.');
          setIsCheckoutSimulating(false);
        }
      } catch (err) {
        console.error(err);
        alert('결제 처리 중 오류가 발생했습니다.');
        setIsCheckoutSimulating(false);
      }
    }, 2000);
  };

  if (!enableCart) return null;
  if (cart.length === 0 && !isOpen) return null;

  return (
    <>
      {/* Floating Cart Badge Button (Only shows when closed and cart has items) */}
      {!isOpen && cart.length > 0 && (
        <button className="cart-badge-btn" onClick={() => setIsOpen(true)}>
          <span className="cart-icon">🛒</span>
          <span className="cart-count-badge">{cart.reduce((a, b) => a + b.quantity, 0)}</span>
          <span className="cart-label">장바구니 보기</span>
        </button>
      )}

      {/* Cart Drawer Panel */}
      {isOpen && (
        <>
          <div className="cart-overlay active" onClick={() => setIsOpen(false)}></div>
          <div className="cart-drawer active">
            <div className="cart-drawer-header">
              <h3>장바구니</h3>
              <button className="cart-close-btn" onClick={() => setIsOpen(false)}>&times;</button>
            </div>

            {cart.length === 0 ? (
              <div className="cart-empty-message">장바구니가 비어 있습니다.</div>
            ) : (
              <>
                <div className="cart-items-list">
                  {cart.map((c) => (
                    <div key={c.item.id} className="cart-item-row">
                      <div className="cart-item-info">
                        <div className="cart-item-name">{c.item.name}</div>
                        <div className="cart-item-price">{c.item.price}</div>
                      </div>
                      <div className="cart-item-controls">
                        <button onClick={() => updateQuantity(c.item.id, -1)}>-</button>
                        <span>{c.quantity}</span>
                        <button onClick={() => updateQuantity(c.item.id, 1)}>+</button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="cart-form-section">
                  <label htmlFor="tableNumberInput">테이블 번호</label>
                  <input
                    id="tableNumberInput"
                    type="text"
                    placeholder="예: 5번 테이블"
                    value={tableNum}
                    onChange={(e) => setTableNum(e.target.value)}
                  />
                </div>

                <div className="cart-drawer-footer">
                  <div className="cart-total-section">
                    <span>총 주문금액</span>
                    <span className="cart-total-price">₩{getTotalPrice().toLocaleString()}</span>
                  </div>
                  <button className="cart-checkout-btn" onClick={handleOrderSubmit}>
                    {enablePayhere ? '페이히어 결제하기' : '주문하기 (직원 호출)'}
                  </button>
                </div>
              </>
            )}
          </div>
        </>
      )}

      {/* Payhere Simulator Modal */}
      {isCheckoutSimulating && (
        <div className="payhere-modal-overlay">
          <div className="payhere-card-modal">
            {simulationStep === 'input' && (
              <>
                <div className="payhere-modal-header">
                  <span className="payhere-logo">payhere</span>
                  <span className="payhere-title">신용카드 간편결제</span>
                  <button className="payhere-close" onClick={() => setIsCheckoutSimulating(false)}>&times;</button>
                </div>
                
                <div className="payhere-modal-body">
                  <div className="payhere-merchant-box">
                    <div className="merchant-label">가맹점명</div>
                    <div className="merchant-name">{restaurant.name}</div>
                  </div>
                  
                  <div className="payhere-amount-box">
                    <div className="amount-label">결제금액</div>
                    <div className="amount-val">₩{getTotalPrice().toLocaleString()}</div>
                  </div>

                  <div className="payhere-form-group">
                    <label>카드 번호</label>
                    <div className="payhere-card-inputs">
                      <input type="text" value="9410" readOnly />
                      <input type="text" value="2300" readOnly />
                      <input type="text" value="****" readOnly />
                      <input type="text" value="4821" readOnly />
                    </div>
                  </div>

                  <div className="payhere-form-row">
                    <div className="payhere-form-group" style={{ flex: 1 }}>
                      <label>유효기간</label>
                      <input type="text" value="08 / 29" readOnly />
                    </div>
                    <div className="payhere-form-group" style={{ flex: 1 }}>
                      <label>CVC 번호</label>
                      <input type="text" value="***" readOnly />
                    </div>
                  </div>
                  
                  <p className="payhere-guide-text">
                    * 위 결제는 모의 테스트용 시뮬레이션입니다. 결제하기 버튼을 누르면 실제 비용 청구 없이 안전하게 다음 주문 단계로 넘어갑니다.
                  </p>
                </div>

                <div className="payhere-modal-footer">
                  <button className="payhere-btn payhere-btn-cancel" onClick={() => setIsCheckoutSimulating(false)}>결제 취소</button>
                  <button className="payhere-btn payhere-btn-submit" onClick={executeMockPayment}>결제하기</button>
                </div>
              </>
            )}

            {simulationStep === 'processing' && (
              <div className="payhere-loading-state">
                <div className="payhere-spinner"></div>
                <h3>페이히어 결제 요청 중...</h3>
                <p>보안 토큰을 발급하고 가맹점 은행 승인을 대기 중입니다. 잠시만 기다려 주세요.</p>
              </div>
            )}

            {simulationStep === 'success' && (
              <div className="payhere-success-state">
                <div className="success-icon">✓</div>
                <h3>결제 완료 및 주문 접수</h3>
                <p className="success-msg">주문이 성공적으로 주방 POS로 전송되었습니다!</p>
                
                <div className="success-receipt">
                  <div className="receipt-row"><span>가맹점</span><strong>{restaurant.name}</strong></div>
                  <div className="receipt-row"><span>테이블</span><strong>{tableNum}</strong></div>
                  <div className="receipt-row"><span>주문 번호</span><strong>#{createdOrderId}</strong></div>
                  <div className="receipt-row"><span>결제 금액</span><strong className="receipt-total">₩{getTotalPrice().toLocaleString()}</strong></div>
                </div>
                
                <p className="receipt-footer">음식이 준비되는 동안 잠시만 기다려 주세요.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
