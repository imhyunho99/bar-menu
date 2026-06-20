'use client';

import { createContext, useContext } from 'react';
import type { RestaurantDetail, CategoryTree } from '@/lib/types';

interface RestaurantContextValue {
  restaurant: RestaurantDetail;
  categoryTree: CategoryTree[];
}

const RestaurantContext = createContext<RestaurantContextValue | null>(null);

export function RestaurantProvider({
  restaurant,
  categoryTree,
  children,
}: RestaurantContextValue & { children: React.ReactNode }) {
  return (
    <RestaurantContext.Provider value={{ restaurant, categoryTree }}>
      {children}
    </RestaurantContext.Provider>
  );
}

export function useRestaurant() {
  const ctx = useContext(RestaurantContext);
  if (!ctx) throw new Error('useRestaurant must be used within RestaurantProvider');
  return ctx;
}
