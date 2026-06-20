'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRestaurant } from '@/app/[restaurantSlug]/context';
import type { CategoryTree } from '@/lib/types';

function CategoryNode({ cat, slug, currentCategoryId }: {
  cat: CategoryTree;
  slug: string;
  currentCategoryId?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasChildren = cat.sub_categories && cat.sub_categories.length > 0;
  if (cat.category_image) return null; // 이미지 전용 카테고리 숨김

  return (
    <li className="top-category">
      <div className="category-header" onClick={hasChildren ? () => setExpanded(!expanded) : undefined}>
        {hasChildren && (
          <span className="toggle-icon">{expanded ? '▼' : '▶'}</span>
        )}
        <Link
          href={`/${slug}/category/${cat.id}`}
          className={cat.id === currentCategoryId ? 'current' : ''}
        >
          {cat.name_en && <div className="category-name-en">{cat.name_en}</div>}
          <div className="category-name-ko">{cat.name}</div>
        </Link>
      </div>
      {hasChildren && expanded && (
        <ul className="sub-categories">
          {cat.sub_categories.map((sub) => {
            if (sub.category_image) return null;
            return (
              <li key={sub.id}>
                <Link
                  href={`/${slug}/category/${sub.id}`}
                  className={sub.id === currentCategoryId ? 'current' : ''}
                >
                  {sub.name_en && <div className="category-name-en">{sub.name_en}</div>}
                  <div className="category-name-ko">{sub.name}</div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </li>
  );
}

export default function SideMenu({ currentCategoryId }: { currentCategoryId?: number }) {
  const { restaurant, categoryTree } = useRestaurant();
  const slug = restaurant.slug;

  const close = () => {
    document.getElementById('sideMenu')?.classList.remove('active');
    document.getElementById('menuOverlay')?.classList.remove('active');
  };

  return (
    <>
      <div className="side-menu" id="sideMenu">
        <div className="side-menu-header">
          <h3>목차</h3>
          <button className="close-menu" onClick={close}>×</button>
        </div>
        <div className="side-menu-content">
          <ul className="category-nav">
            <li><Link href={`/${slug}`} onClick={close}>홈</Link></li>
            {categoryTree.map((cat) => (
              <CategoryNode key={cat.id} cat={cat} slug={slug} currentCategoryId={currentCategoryId} />
            ))}
          </ul>
        </div>
      </div>
      <div className="menu-overlay" id="menuOverlay" onClick={close} />
    </>
  );
}
