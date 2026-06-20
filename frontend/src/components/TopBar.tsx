'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { searchMenu } from '@/lib/api';
import { useRestaurant } from '@/app/[restaurantSlug]/context';
import type { SearchResult } from '@/lib/types';

export default function TopBar() {
  const { restaurant } = useRestaurant();
  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const slug = restaurant.slug;

  const handleSearch = useCallback(async (q: string) => {
    if (q.length < 2) { setResults([]); return; }
    try {
      const data = await searchMenu(slug, q);
      setResults(data.results);
    } catch { setResults([]); }
  }, [slug]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => handleSearch(query), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, handleSearch]);

  const openSearch = () => {
    setSearchOpen(true);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const closeSearch = () => {
    setSearchOpen(false);
    setQuery('');
    setResults([]);
  };

  const handleResultClick = (result: SearchResult) => {
    closeSearch();
    if (result.type === 'category') {
      router.push(`/${slug}/category/${result.id}`);
    } else if (result.category_id) {
      router.push(`/${slug}/category/${result.category_id}#menu-${result.id}`);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    // 서버사이드 검색 리다이렉트 (첫 번째 결과로 이동)
    if (results.length > 0) {
      handleResultClick(results[0]);
    }
  };

  return (
    <div className="top-bar">
      {!searchOpen && (
        <div className="top-bar-buttons" id="topBarButtons">
          <button className="search-toggle" onClick={openSearch}>
            <Image src="/search.png" alt="Search" width={60} height={60} />
          </button>
          <button className="menu-toggle" onClick={() => {
            document.getElementById('sideMenu')?.classList.add('active');
            document.getElementById('menuOverlay')?.classList.add('active');
          }}>
            <Image src="/menu.png" alt="Menu" width={60} height={60} />
          </button>
        </div>
      )}
      {searchOpen && (
        <form className="search-container" style={{ display: 'flex' }} onSubmit={handleSubmit}>
          <div className="search-input-wrapper">
            <input
              ref={inputRef}
              type="text"
              id="searchInput"
              name="q"
              placeholder="메뉴 검색..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              required
            />
            <button type="button" className="search-close" onClick={closeSearch}>×</button>
          </div>
          {results.length > 0 && (
            <div className="search-results" id="searchResults">
              {results.map((r, i) => (
                <div key={i} className="search-result-item" onClick={() => handleResultClick(r)}>
                  <div className="search-result-title">{r.title}</div>
                  <div className="search-result-subtitle">{r.subtitle}</div>
                </div>
              ))}
            </div>
          )}
        </form>
      )}
    </div>
  );
}
