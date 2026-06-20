'use client';

import { useState, useEffect, useRef } from 'react';
import type { MenuItem as MenuItemType } from '@/lib/types';

/** nl2br: 줄바꿈을 <br>로 변환 */
function Nl2br({ text }: { text: string | null | undefined }) {
  if (!text) return null;
  return <>{text.split('\n').map((line, i) => <span key={i}>{line}{i < text.split('\n').length - 1 && <br />}</span>)}</>;
}

// ===== Lightbox =====
function Lightbox({ src, alt, style, opacity, onClose }: {
  src: string; alt: string; style: string; opacity: number; onClose: () => void;
}) {
  const [active, setActive] = useState(false);
  useEffect(() => { requestAnimationFrame(() => setActive(true)); }, []);

  return (
    <div
      className={`lightbox-overlay style-${style} ${active ? 'active' : ''}`}
      style={{ background: `rgba(0,0,0,${opacity / 100})` }}
      onClick={onClose}
    >
      <button className="lightbox-close" onClick={onClose}>&times;</button>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} onClick={(e) => e.stopPropagation()} />
    </div>
  );
}

// ===== Detail Modal =====
function DetailModal({ item, opacity, onClose }: {
  item: MenuItemType; opacity: number; onClose: () => void;
}) {
  const hasPairings = item.pairings && item.pairings.length > 0;
  const imgSrc = item.detail_image || item.menu_image;

  return (
    <div className="detail-modal-overlay active" style={{ background: `rgba(0,0,0,${opacity / 100})` }} onClick={onClose}>
      <div className={`detail-modal ${hasPairings ? 'has-pairings' : ''}`} onClick={(e) => e.stopPropagation()}>
        <button className="detail-modal-close" onClick={onClose}>&times;</button>
        {imgSrc && (
          <div className="detail-modal-image-wrap">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imgSrc} alt={item.name} />
          </div>
        )}
        <div className="detail-modal-body">
          <div className="detail-modal-title">
            {item.name_en && <span className="menu-name-en"><Nl2br text={item.name_en} /></span>}
            <span className="menu-name-ko"><Nl2br text={item.name} /></span>
          </div>
          {(item.detail_description || item.description) && (
            <div className="detail-modal-desc"><Nl2br text={item.detail_description || item.description} /></div>
          )}
          <div className="detail-modal-footer">
            {item.notes ? <span className="menu-notes"><Nl2br text={item.notes} /></span> : <span />}
            <span className="menu-price"><Nl2br text={item.price} /></span>
          </div>
          {hasPairings && (
            <div className="detail-modal-pairings" style={{ display: 'block' }}>
              <div className="pairings-heading">추천 페어링</div>
              <div className="pairings-container">
                {item.pairings.map((p) => (
                  <div key={p.id} className="pairing-item-card">
                    {p.image && (
                      <div className="pairing-item-image">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={p.image} alt={p.name} />
                      </div>
                    )}
                    <div className="pairing-item-info">
                      <div className="pairing-item-name">{p.name}</div>
                      {p.description && <div className="pairing-item-desc"><Nl2br text={p.description} /></div>}
                      {p.price && <div className="pairing-item-price">{p.price}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ===== MenuCard =====
export default function MenuCard({ item }: { item: MenuItemType }) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const itemRef = useRef<HTMLDivElement>(null);

  // target=ID로 스크롤
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('target') === String(item.id)) {
        setTimeout(() => itemRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 300);
      }
      if (window.location.hash === `#menu-${item.id}`) {
        setTimeout(() => itemRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 300);
      }
    }
  }, [item.id]);

  const handleItemClick = () => {
    if (item.enable_detail_view) setDetailOpen(true);
  };

  const handleExpandClick = (e: React.MouseEvent) => {
    if (item.click_expand && item.menu_image) {
      e.stopPropagation();
      setLightboxOpen(true);
    }
  };

  const mode = item.display_mode;

  return (
    <>
      <div
        ref={itemRef}
        className={`menu-item${mode === 'combined' ? ' menu-item-combined' : ''}`}
        id={`menu-${item.id}`}
        data-detail={item.enable_detail_view ? 'true' : undefined}
        onClick={handleItemClick}
      >
        {mode === 'combined' && item.menu_image ? (
          <>
            <div
              className="menu-combined-image"
              data-expand={item.click_expand || undefined}
              onClick={handleExpandClick}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={item.menu_image} alt={item.name} loading="lazy" />
            </div>
            <div className="menu-combined-text">
              <div className="menu-title">
                {item.name_en && <span className="menu-name-en"><Nl2br text={item.name_en} /></span>}
                <span className="menu-name-ko"><Nl2br text={item.name} /></span>
              </div>
              {item.description && <div className="menu-description"><Nl2br text={item.description} /></div>}
              <div className="menu-notes-price-wrapper" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                {item.notes ? <span className="menu-notes"><Nl2br text={item.notes} /></span> : <span />}
                <div className="menu-price"><Nl2br text={item.price} /></div>
              </div>
            </div>
          </>
        ) : (mode === 'image_only' || (mode === 'auto' && item.menu_image)) && item.menu_image ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={item.menu_image}
            alt={item.name}
            className="menu-only-image"
            loading="lazy"
            data-expand={item.click_expand || undefined}
            onClick={handleExpandClick}
          />
        ) : (
          <div className="menu-content">
            <div className="menu-info">
              <div className="menu-title-line">
                <div className="menu-title">
                  {item.name_en && <span className="menu-name-en"><Nl2br text={item.name_en} /></span>}
                  <span className="menu-name-ko"><Nl2br text={item.name} /></span>
                </div>
              </div>
              {item.description && <div className="menu-description"><Nl2br text={item.description} /></div>}
              <div className="menu-notes-price-wrapper" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                {item.notes ? <span className="menu-notes"><Nl2br text={item.notes} /></span> : <span />}
                <div className="menu-price"><Nl2br text={item.price} /></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {lightboxOpen && item.menu_image && (
        <Lightbox
          src={item.menu_image}
          alt={item.name}
          style={item.lightbox_style}
          opacity={item.lightbox_opacity}
          onClose={() => setLightboxOpen(false)}
        />
      )}
      {detailOpen && (
        <DetailModal
          item={item}
          opacity={item.lightbox_opacity}
          onClose={() => setDetailOpen(false)}
        />
      )}
    </>
  );
}
