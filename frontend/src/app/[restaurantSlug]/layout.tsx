import { getRestaurant, getCategoryTree } from '@/lib/api';
import { buildCSSVariables, buildFontFaces } from '@/lib/styles';
import type { RestaurantDetail, CategoryTree } from '@/lib/types';
import { RestaurantProvider } from './context';

export default async function RestaurantLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ restaurantSlug: string }>;
}) {
  const { restaurantSlug } = await params;
  let restaurant: RestaurantDetail;
  let categoryTree: CategoryTree[];

  try {
    [restaurant, categoryTree] = await Promise.all([
      getRestaurant(restaurantSlug),
      getCategoryTree(restaurantSlug),
    ]);
  } catch {
    return <div style={{ color: '#fff', padding: '2rem', textAlign: 'center' }}>매장을 찾을 수 없습니다.</div>;
  }

  const settings = restaurant.site_settings;
  const cssVars = buildCSSVariables(settings);
  const fontFaces = buildFontFaces(settings);

  return (
    <>
      {(cssVars || fontFaces) && (
        <style dangerouslySetInnerHTML={{ __html: `${fontFaces}\n${cssVars}` }} />
      )}
      {settings?.side_image && (
        <style dangerouslySetInnerHTML={{
          __html: `body { background: url('${settings.side_image}'); background-size: cover; background-position: center; background-attachment: fixed; }`
        }} />
      )}
      <RestaurantProvider restaurant={restaurant} categoryTree={categoryTree}>
        <div style={{ backgroundColor: settings?.background_color || '#000000', minHeight: '100vh' }}>
          {children}
        </div>
      </RestaurantProvider>
    </>
  );
}
