import { getRestaurant, getCategoryDetail, getCategoryTree } from '@/lib/api';
import TopBar from '@/components/TopBar';
import SideMenu from '@/components/SideMenu';
import MenuCard from '@/components/MenuCard';
import NavigationRemote from '@/components/NavigationRemote';
import Link from 'next/link';
import type { Metadata } from 'next';
import type { CategoryTree } from '@/lib/types';
import Cart from '@/components/Cart';
import WifiHelper from '@/components/WifiHelper';

export const revalidate = 60; // 60초마다 ISR 재생성

export async function generateMetadata({
  params,
}: {
  params: Promise<{ restaurantSlug: string; categoryId: string }>;
}): Promise<Metadata> {
  const { restaurantSlug, categoryId } = await params;
  try {
    const [restaurant, category] = await Promise.all([
      getRestaurant(restaurantSlug),
      getCategoryDetail(restaurantSlug, parseInt(categoryId)),
    ]);
    return {
      title: `${category.name} | ${restaurant.name} 메뉴판`,
      description: `${restaurant.name}의 ${category.name} 카테고리 메뉴 목록입니다.`,
    };
  } catch {
    return {
      title: '메뉴 목록',
    };
  }
}

/**
 * 카테고리 트리에서 이미지 전용이 아닌(a 태그로 이동 가능한) 리프 카테고리들을 순서대로 추출
 */
function getFlatCategories(tree: CategoryTree[]): { id: number; name: string }[] {
  const list: { id: number; name: string }[] = [];
  const traverse = (node: CategoryTree) => {
    // 이미지 전용 카테고리는 플랫 목록에서 제외 (리모컨 이동 대상 제외)
    if (node.category_image) return;

    const hasChildren = node.sub_categories && node.sub_categories.length > 0;
    if (!hasChildren) {
      list.push({ id: node.id, name: node.name });
    } else {
      // 자식이 있다면 자식 노드들을 순회
      node.sub_categories.forEach(traverse);
    }
  };
  tree.forEach(traverse);
  return list;
}

import { notFound } from 'next/navigation';

export default async function CategoryDetailPage({
  params,
}: {
  params: Promise<{ restaurantSlug: string; categoryId: string }>;
}) {
  const { restaurantSlug, categoryId } = await params;
  const currentCatId = parseInt(categoryId);

  let restaurant;
  let category;
  let tree;

  try {
    [restaurant, category, tree] = await Promise.all([
      getRestaurant(restaurantSlug),
      getCategoryDetail(restaurantSlug, currentCatId),
      getCategoryTree(restaurantSlug),
    ]);
  } catch (error) {
    console.error('Failed to fetch category detail or tree:', error);
    notFound();
  }

  const settings = restaurant.site_settings;
  const flatCats = getFlatCategories(tree);
  
  const currentIndex = flatCats.findIndex((c) => c.id === currentCatId);
  let prevCategory = null;
  let nextCategory = null;
  
  if (currentIndex !== -1 && flatCats.length > 1) {
    const prevIdx = (currentIndex - 1 + flatCats.length) % flatCats.length;
    const nextIdx = (currentIndex + 1) % flatCats.length;
    prevCategory = flatCats[prevIdx];
    nextCategory = flatCats[nextIdx];
  }

  const isSubcategoryView = category.sub_categories && category.sub_categories.length > 0;
  const hasMenuItems = category.menu_items && category.menu_items.length > 0;

  // 첫 번째 카테고리가 이미지가 없거나 메뉴아이템 첫 번째가 이미지가 없거나 텍스트 온리인 경우 top-bar-spacing 클래스를 적용하여 탑바와 겹치지 않게 처리
  let needsSpacing = true;
  if (isSubcategoryView) {
    const firstSub = category.sub_categories[0];
    if (firstSub && firstSub.category_image) {
      needsSpacing = false;
    }
  } else if (hasMenuItems) {
    const firstItem = category.menu_items[0];
    if (firstItem && firstItem.menu_image && firstItem.display_mode !== 'text_only' && firstItem.display_mode !== 'combined') {
      needsSpacing = false;
    }
  }

  return (
    <>
      {/* 배경 그라데이션 레이아웃 */}
      {settings?.side_image && <div className="background-with-gradient" />}

      <TopBar />
      <SideMenu currentCategoryId={currentCatId} />

      <div className={`menu-container${needsSpacing ? ' top-bar-spacing' : ''}`}>
        <main className="main" style={{ padding: '0', margin: '0' }}>
          <div className="container" style={{ padding: '0', margin: '0', maxWidth: 'none' }}>
            
            {/* 1. 하위 카테고리 그리드 뷰 (category_list.html) */}
            {isSubcategoryView && (
              <div className="category-section" style={{ margin: '0', padding: '0' }}>
                <div className="category-grid">
                  {category.sub_categories.map((sub) => (
                    <div className="category-item" key={sub.id}>
                      {sub.category_image ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={sub.category_image}
                          alt={sub.name}
                          className="category-only-image"
                        />
                      ) : (
                        <Link
                          href={`/${restaurantSlug}/category/${sub.id}`}
                          className="category-content"
                        >
                          {sub.name_en && (
                            <h4 className="category-name-en">{sub.name_en}</h4>
                          )}
                          <h3 className="category-name-ko">{sub.name}</h3>
                        </Link>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 2. 메뉴 목록 그리드 뷰 (menu_list.html) */}
            {!isSubcategoryView && (
              <div className="menu-grid" id="menuGrid" style={{ margin: '0', padding: '0' }}>
                {category.menu_items.map((item) => (
                  <MenuCard key={item.id} item={item} />
                ))}

                {category.menu_items.length === 0 && (
                  <div className="no-menu">
                    등록된 메뉴가 없습니다.
                  </div>
                )}
              </div>
            )}

          </div>
        </main>
      </div>

      {/* 리모컨 컴포넌트 */}
      {!isSubcategoryView && (
        <NavigationRemote
          slug={restaurantSlug}
          prevCategory={prevCategory}
          nextCategory={nextCategory}
        />
      )}

      <Cart />
      <WifiHelper />
    </>
  );
}
