// 공통 JavaScript 함수들

class MenuApp {
    constructor() {
        this.searchTimeout = null;
        this.loadingScreen = null;
        this.loadingVideo = null;
        this.videoEnded = false;
        this.init();
    }

    init() {
        // 브라우저가 멋대로 스크롤 위치를 복원하지 않도록 설정
        if ('scrollRestoration' in history) {
            history.scrollRestoration = 'manual';
        }

        this.initElements();
        this.bindEvents();
        this.initPageLoadActions();
    }

    initElements() {
        // 사이드 메뉴 요소들
        this.menuToggle = document.getElementById('menuToggle');
        this.sideMenu = document.getElementById('sideMenu');
        this.menuOverlay = document.getElementById('menuOverlay');
        this.closeMenu = document.getElementById('closeMenu');

        // 검색 요소들
        this.searchToggle = document.getElementById('searchToggle');
        this.searchContainer = document.getElementById('searchContainer');
        this.searchInput = document.getElementById('searchInput');
        this.searchClose = document.getElementById('searchClose');
        this.searchResults = document.getElementById('searchResults');
        this.topBarButtons = document.getElementById('topBarButtons');

        // 로딩 스크린 요소들
        this.loadingScreen = document.getElementById('loading-screen');
        this.loadingVideo = document.getElementById('loadingVideo');
        this.loadingVideo2 = document.getElementById('loadingVideo2');

        // 리모컨 요소들
        this.navigationRemote = document.getElementById('navigationRemote');
        this.remoteTop = document.getElementById('remoteTop');
        this.remotePrev = document.getElementById('remotePrev');
        this.remoteNext = document.getElementById('remoteNext');

        // 상세 모달 요소들
        this.detailOverlay = document.getElementById('detailModalOverlay');
        this.detailClose = document.getElementById('detailModalClose');
        this.detailImage = document.getElementById('detailModalImage');
        this.detailImageWrap = document.getElementById('detailModalImageWrap');
        this.detailNameKo = document.getElementById('detailModalNameKo');
        this.detailNameEn = document.getElementById('detailModalNameEn');
        this.detailDesc = document.getElementById('detailModalDesc');
        this.detailNotes = document.getElementById('detailModalNotes');
        this.detailPrice = document.getElementById('detailModalPrice');

        // 라이트박스 요소들
        this.lightboxOverlay = document.getElementById('lightboxOverlay');
        this.lightboxClose = document.getElementById('lightboxClose');
        this.lightboxImage = document.getElementById('lightboxImage');
    }

    bindEvents() {
        // 사이드 메뉴 이벤트
        if (this.menuToggle) {
            this.menuToggle.addEventListener('click', () => this.openMenu());
            if (this.closeMenu) {
                this.closeMenu.addEventListener('click', () => this.closeMenuFunc());
            }
            if (this.menuOverlay) {
                this.menuOverlay.addEventListener('click', () => this.closeMenuFunc());
            }
        }

        // 검색 이벤트
        if (this.searchToggle) {
            this.searchToggle.addEventListener('click', () => this.openSearch());
            if (this.searchClose) {
                this.searchClose.addEventListener('click', () => this.closeSearch());
            }
            if (this.searchInput) {
                this.searchInput.addEventListener('input', () => this.performSearch());
            }
        }

        // 스크롤 배경 효과
        this.initScrollBackground();

        // 리모컨 이벤트
        this.initNavigationRemote();
        
        // 리모컨 높이 조절
        window.addEventListener('load', () => this.adjustRemoteTopHeight());
        window.addEventListener('resize', () => this.adjustRemoteTopHeight());

        // 상세 모달 이벤트
        this.initDetailModal();

        // 라이트박스 이벤트
        this.initLightbox();
    }
    
    initPageLoadActions() {
        // 로딩 스크린 초기화
        this.initLoadingScreen();

        // 페이지 로드 시 스크롤
        document.addEventListener('DOMContentLoaded', () => {
            this.scrollToTarget();
            this.scrollToAnchor();
        });
        window.addEventListener('load', () => {
            setTimeout(() => {
                this.scrollToTarget();
                this.scrollToAnchor();
            }, 100); 
        });
        window.addEventListener('hashchange', () => this.scrollToAnchor());
    }

    // ==========================================
    // 로딩 스크린 기능
    // ==========================================
    initLoadingScreen() {
        if (!this.loadingScreen || !this.loadingVideo) return;

        // [중요] 비디오 1(인트로)과 비디오 2(설명서)에 이벤트 리스너를 미리 심어둠
        // (1시간 이내 시청 기록이 있어 'return' 되더라도 설명서는 작동해야 하므로)
        
        // 1. 첫 번째 비디오(인트로) 이벤트
        this.loadingVideo.addEventListener('ended', () => {
            this.playSecondaryVideoOrFinish();
        });

        this.loadingVideo.addEventListener('error', () => {
            console.log('Main video failed to load, using fallback');
            setTimeout(() => this.playSecondaryVideoOrFinish(), 3000);
        });

        // 2. 두 번째 비디오(loadingVideo2, 메뉴판 설명서) 이벤트 연동
        if (this.loadingVideo2) {
            const skipVideoTwo = (e) => {
                if (e && e.cancelable) e.preventDefault();
                this.videoEnded = true;
                this.hideLoadingScreen();
            };
            
            // 종료되거나 사용자가 탭/클릭하면 스킵
            this.loadingVideo2.addEventListener('ended', skipVideoTwo);
            this.loadingVideo2.addEventListener('click', skipVideoTwo);
            this.loadingVideo2.addEventListener('touchstart', skipVideoTwo, { passive: false });
            this.loadingVideo2.addEventListener('error', skipVideoTwo);
        }

        // 3. 로딩 화면(배경) 전체 터치 시 닫기 (모바일 인식률 향상을 위한 안전 장치)
        // (단, 인트로 영상이 아닌 '설명서 영상(video2)' 재생 중에만 동작하도록 유도)
        this.loadingScreen.addEventListener('click', (e) => {
            if (this.loadingVideo2 && this.loadingVideo2.style.display === 'block') {
                this.videoEnded = true;
                this.hideLoadingScreen();
            }
        });

        // [체크] 이제 인트로 영상 캐시를 체크하여 스킵 여부를 결정함
        const lastIntroTime = localStorage.getItem('lastIntroTime');
        const currentTime = Date.now();
        const oneHour = 60 * 60 * 1000;

        if (lastIntroTime && (currentTime - parseInt(lastIntroTime)) < oneHour) {
            // 1시간 이내에 본 경우 인트로 영상만 안 보여주고 바로 빠져나감
            // (하지만 위에서 설정한 이벤트 리스너들은 이미 메모리에 살아있음)
            this.loadingScreen.style.display = 'none';
            return;
        }

        // 인트로 시청 시간 저장
        localStorage.setItem('lastIntroTime', currentTime.toString());

        // 비디오가 5초 내에 시작되지 않으면 다음으로 진행
        const fallbackTimeout = setTimeout(() => {
            if (!this.videoEnded && this.loadingVideo.currentTime === 0) {
                this.playSecondaryVideoOrFinish();
            }
        }, 5000);

        this.loadingVideo.addEventListener('playing', () => clearTimeout(fallbackTimeout));
    }

    playSecondaryVideoOrFinish() {
        if (this.loadingVideo2) {
            this.loadingVideo.style.display = 'none';
            this.loadingVideo2.style.display = 'block';
            this.loadingVideo2.play().catch(e => {
                this.videoEnded = true;
                this.hideLoadingScreen();
            });
        } else {
            this.videoEnded = true;
            this.hideLoadingScreen();
        }
    }

    showManualVideo() {
        if (!this.loadingScreen || !this.loadingVideo2) return;

        // 로딩 스크린 상태 초기화 (재사용 가능하도록)
        this.loadingScreen.classList.remove('door-open');
        this.loadingScreen.style.display = 'flex';
        this.loadingScreen.style.opacity = '1';

        // 첫 번째 영상 숨기고 두 번째 영상(설명서) 표시
        if (this.loadingVideo) this.loadingVideo.style.display = 'none';
        this.loadingVideo2.style.display = 'block';
        this.loadingVideo2.currentTime = 0;

        // 비디오 재생
        this.loadingVideo2.play().catch(e => {
            console.log('Manual video play failed:', e);
            // 재생 실패 시 닫기 (사용자 클릭으로 실행되므로 대부분 성공함)
            this.hideLoadingScreen();
        });
    }

    hideLoadingScreen() {
        if (!this.loadingScreen) return;
        this.loadingScreen.classList.add('door-open');
        setTimeout(() => {
            // door-open 애니메이션이 끝난 후 hide
            if (this.loadingScreen.classList.contains('door-open')) {
                this.loadingScreen.style.display = 'none';
            }
        }, 500);
    }

    // ==========================================
    // 스크롤 이동 기능
    // ==========================================
    scrollToTarget() {
        const urlParams = new URLSearchParams(window.location.search);
        const targetId = urlParams.get('target');

        if (!targetId) return;

        // 타겟 요소 찾기 (menu-숫자 또는 숫자 ID)
        let targetElement = document.getElementById('menu-' + targetId);
        if (!targetElement) targetElement = document.getElementById(targetId);

        if (targetElement) {
            // 화면 중앙으로 스크롤 이동
            targetElement.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center',
                inline: 'nearest'
            });
        }
    }

    scrollToAnchor() {
        if (!window.location.hash) return;

        const elementId = window.location.hash.substring(1);
        const element = document.getElementById(elementId);
        
        if (element) {
            element.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center', 
                inline: 'nearest' 
            });
            
            // 백업 방법: 직접 스크롤 계산
            setTimeout(() => {
                const rect = element.getBoundingClientRect();
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const targetY = rect.top + scrollTop - (window.innerHeight / 2) + (rect.height / 2);
                
                window.scrollTo({
                    top: Math.max(0, targetY),
                    behavior: 'smooth'
                });
            }, 200);
        }
    }

    // ==========================================
    // 검색 기능 (UI + Live Search)
    // ==========================================
    openSearch() {
        if (this.searchContainer && this.topBarButtons) {
            this.topBarButtons.style.display = 'none';
            this.searchContainer.style.display = 'flex';
            if (this.searchInput) {
                this.searchInput.focus();
            }
        }
    }

    closeSearch() {
        if (this.searchContainer && this.topBarButtons) {
            this.searchContainer.style.display = 'none';
            this.topBarButtons.style.display = 'flex';
            if (this.searchInput) {
                this.searchInput.value = '';
            }
            if (this.searchResults) {
                this.searchResults.innerHTML = '';
            }
        }
    }

    getApiUrl() {
        if (window.searchApiUrl) return window.searchApiUrl;
        
        // 현재 경로에서 첫 번째 세그먼트(slug) 추출 시도
        // 예: /bid/menu/... -> bid
        const pathSegments = window.location.pathname.split('/').filter(p => p);
        if (pathSegments.length > 0) {
            const slug = pathSegments[0];
            // admin, static, media 등 예약된 경로가 아닐 때만 사용
            if (!['admin', 'static', 'media', 'qr'].includes(slug)) {
                return `/${slug}/api/search/`;
            }
        }
        return '/api/search/';
    }

    performSearch() {
        const query = this.searchInput.value.trim();
        if (query.length < 2) {
            this.searchResults.innerHTML = '';
            return;
        }

        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            const apiUrl = this.getApiUrl();
            fetch(`${apiUrl}?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => this.displaySearchResults(data.results))
                .catch(error => console.error(error));
        }, 300);
    }

    displaySearchResults(results) {
        if (results.length === 0) {
            this.searchResults.innerHTML = '<div class="search-no-results">검색 결과가 없습니다.</div>';
            return;
        }

        const html = results.map(result => `
            <div class="search-result-item" onclick="window.menuApp.handleSearchClick('${result.url}')">
                <div class="search-result-title">${result.title}</div>
                <div class="search-result-subtitle">${result.subtitle}</div>
            </div>
        `).join('');

        this.searchResults.innerHTML = html;
    }

    handleSearchClick(url) {
        this.closeSearch();
        
        if (url.includes('#')) {
            const [baseUrl, anchor] = url.split('#');
            const currentPath = window.location.pathname;
            
            // URL 정규화 (끝의 슬래시 제거)
            const normalizedBaseUrl = baseUrl.replace(/\/$/, '');
            const normalizedCurrentPath = currentPath.replace(/\/$/, '');
            
            if (normalizedBaseUrl === normalizedCurrentPath) {
                // 같은 페이지 내 앵커로 즉시 이동
                const element = document.getElementById(anchor);
                if (element) {
                    element.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center', 
                        inline: 'nearest' 
                    });
                    history.pushState(null, null, '#' + anchor);
                }
            } else {
                // 다른 페이지로 이동 - target 파라미터로 변환
                const cleanId = anchor.replace('menu-', '');
                const separator = baseUrl.includes('?') ? '&' : '?';
                window.location.href = `${baseUrl}${separator}target=${cleanId}`;
            }
        } else {
            window.location.href = url;
        }
    }

    // ==========================================
    // 사이드 메뉴 기능
    // ==========================================
    openMenu() {
        if (this.sideMenu) this.sideMenu.classList.add('active');
        if (this.menuOverlay) this.menuOverlay.classList.add('active');
    }

    closeMenuFunc() {
        if (this.sideMenu) this.sideMenu.classList.remove('active');
        if (this.menuOverlay) this.menuOverlay.classList.remove('active');
    }

    toggleCategory(categoryId) {
        const subCategories = document.getElementById('sub-' + categoryId);
        const icon = document.getElementById('icon-' + categoryId);
        if (subCategories.style.display === 'none') {
            subCategories.style.display = 'block';
            icon.textContent = '▼';
        } else {
            subCategories.style.display = 'none';
            icon.textContent = '▶';
        }
    }
    
    // 스크롤 배경 효과
    initScrollBackground() {
        const background = document.querySelector('.background-with-gradient');
        if (background) {
            window.addEventListener('scroll', () => {
                const scrollPercent = Math.min(window.scrollY / (document.documentElement.scrollHeight - window.innerHeight), 1);
                const scale = 1 + (scrollPercent * 1.8);
                background.style.transform = `scale(${scale})`;
            });
        }
    }

    // ==========================================
    // 리모컨 기능
    // ==========================================
    initNavigationRemote() {
        if (!this.navigationRemote) return;

        // 맨 위로 버튼
        if (this.remoteTop) {
            this.remoteTop.addEventListener('click', () => this.scrollToTop());
        }

        // 이전 카테고리 버튼
        if (this.remotePrev && window.navigationData && window.navigationData.prevUrl) {
            this.remotePrev.addEventListener('click', () => {
                window.location.href = window.navigationData.prevUrl;
            });
        } else if (this.remotePrev) {
            this.remotePrev.style.display = 'none';
        }

        // 다음 카테고리 버튼
        if (this.remoteNext && window.navigationData && window.navigationData.nextUrl) {
            this.remoteNext.addEventListener('click', () => {
                window.location.href = window.navigationData.nextUrl;
            });
        } else if (this.remoteNext) {
            this.remoteNext.style.display = 'none';
        }
    }

    scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    adjustRemoteTopHeight() {
        if (this.remoteTop) {
            let targetHeight = 0;
            // Get height from next or prev buttons
            if (this.remoteNext && this.remoteNext.offsetHeight > 0) {
                targetHeight = this.remoteNext.offsetHeight;
            } else if (this.remotePrev && this.remotePrev.offsetHeight > 0) {
                targetHeight = this.remotePrev.offsetHeight;
            }

            if (targetHeight > 0) {
                this.remoteTop.style.height = `${targetHeight}px`;
            }
        }
    }

    // ==========================================
    // 상세 모달 기능
    // ==========================================
    initDetailModal() {
        if (!this.detailOverlay) return;

        // 이벤트 위임: menu-item 클릭 시 detail 데이터가 있으면 모달 열기
        const menuGrid = document.getElementById('menuGrid');
        if (menuGrid) {
            menuGrid.addEventListener('click', (e) => {
                // 라이트박스 이미지 클릭은 제외 (data-expand가 있는 경우)
                if (e.target.closest('[data-expand]')) return;

                const menuItem = e.target.closest('.menu-item[data-detail="true"]');
                if (menuItem) {
                    this.openDetailModal(menuItem);
                }
            });
        }

        // 닫기 버튼
        if (this.detailClose) {
            this.detailClose.addEventListener('click', () => this.closeDetailModal());
        }

        // 오버레이 클릭으로 닫기
        this.detailOverlay.addEventListener('click', (e) => {
            if (e.target === this.detailOverlay) {
                this.closeDetailModal();
            }
        });

        // ESC 키로 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.detailOverlay.classList.contains('active')) {
                this.closeDetailModal();
            }
        });
    }

    openDetailModal(menuItem) {
        const data = menuItem.dataset;

        // 이미지
        if (data.detailImg) {
            this.detailImage.src = data.detailImg;
            this.detailImage.alt = data.detailName || '';
            this.detailImageWrap.style.display = 'block';
        } else {
            this.detailImage.src = '';
            this.detailImageWrap.style.display = 'none';
        }

        // 텍스트
        this.detailNameKo.textContent = data.detailName || '';
        this.detailNameEn.textContent = data.detailNameEn || '';
        this.detailNameEn.style.display = data.detailNameEn ? 'block' : 'none';
        this.detailDesc.textContent = data.detailDesc || '';
        this.detailDesc.style.display = data.detailDesc ? 'block' : 'none';
        this.detailNotes.textContent = data.detailNotes || '';
        this.detailNotes.style.display = data.detailNotes ? 'inline' : 'none';
        this.detailPrice.textContent = data.detailPrice || '';

        // 투명도(불투명도) 적용
        const opacity = data.detailOpacity || '35';
        const op = parseInt(opacity) / 100;
        this.detailOverlay.style.backgroundColor = `rgba(0, 0, 0, ${op})`;

        // 추천 페어링 연동
        const pairingsSection = document.getElementById('detailModalPairingsSection');
        const pairingsContainer = document.getElementById('detailModalPairingsContainer');
        const modalEl = this.detailOverlay.querySelector('.detail-modal');
        if (pairingsSection && pairingsContainer) {
            const pairingsData = menuItem.querySelector('.menu-item-pairings-data');
            if (pairingsData && pairingsData.children.length > 0) {
                pairingsContainer.innerHTML = pairingsData.innerHTML;
                pairingsSection.style.display = 'block';
                if (modalEl) modalEl.classList.add('has-pairings');
            } else {
                pairingsContainer.innerHTML = '';
                pairingsSection.style.display = 'none';
                if (modalEl) modalEl.classList.remove('has-pairings');
            }
        }

        // 모달 열기
        this.detailOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    closeDetailModal() {
        this.detailOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    // ==========================================
    // 라이트박스 기능 (이미지 확대)
    // ==========================================
    initLightbox() {
        if (!this.lightboxOverlay) return;

        // 이벤트 위임: data-expand 속성이 있는 요소 클릭
        document.addEventListener('click', (e) => {
            const expandEl = e.target.closest('[data-expand]');
            if (expandEl) {
                e.preventDefault();
                e.stopPropagation();
                const src = expandEl.dataset.expandSrc;
                const alt = expandEl.dataset.expandAlt || '';
                const style = expandEl.dataset.expandStyle || 'zoom';
                const opacity = expandEl.dataset.expandOpacity || '35';
                if (src) {
                    this.openLightbox(src, alt, style, opacity);
                }
            }
        });

        // 닫기
        if (this.lightboxClose) {
            this.lightboxClose.addEventListener('click', () => this.closeLightbox());
        }
        this.lightboxOverlay.addEventListener('click', (e) => {
            if (e.target === this.lightboxOverlay || e.target === this.lightboxImage) {
                this.closeLightbox();
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.lightboxOverlay.classList.contains('active')) {
                this.closeLightbox();
            }
        });
    }

    openLightbox(src, alt, style, opacity) {
        this.lightboxImage.src = src;
        this.lightboxImage.alt = alt;
        // 스타일 클래스 적용 (zoom, slide_up, fade)
        this.lightboxOverlay.className = 'lightbox-overlay style-' + (style || 'zoom');
        // 투명도(불투명도) 적용
        const op = parseInt(opacity || '35') / 100;
        this.lightboxOverlay.style.backgroundColor = `rgba(0, 0, 0, ${op})`;
        // display가 항상 flex이므로 곧바로 active 추가하여 자연스럽게 트랜지션 적용
        this.lightboxOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    closeLightbox() {
        this.lightboxOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// 전역 함수로 노출 (템플릿에서 사용)
window.toggleCategory = function(categoryId) {
    if (window.menuApp) {
        window.menuApp.toggleCategory(categoryId);
    }
};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    window.menuApp = new MenuApp();
});