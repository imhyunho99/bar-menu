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

        // 리모컨 요소들
        this.navigationRemote = document.getElementById('navigationRemote');
        this.remoteTop = document.getElementById('remoteTop');
        this.remotePrev = document.getElementById('remotePrev');
        this.remoteNext = document.getElementById('remoteNext');
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

        // 인트로 영상 캐시 체크 (1시간)
        const lastIntroTime = localStorage.getItem('lastIntroTime');
        const currentTime = Date.now();
        const oneHour = 60 * 60 * 1000;

        if (lastIntroTime && (currentTime - parseInt(lastIntroTime)) < oneHour) {
            // 1시간 이내에 본 경우 인트로 완전 스킵
            this.loadingScreen.style.display = 'none';
            return;
        }

        // 인트로 시청 시간 저장
        localStorage.setItem('lastIntroTime', currentTime.toString());

        // 비디오 재생 완료 후 로딩 스크린 제거
        this.loadingVideo.addEventListener('ended', () => {
            this.videoEnded = true;
            this.hideLoadingScreen();
        });

        // 비디오 로드 에러 시 이미지로 대체하고 3초 후 진행
        this.loadingVideo.addEventListener('error', () => {
            console.log('Video failed to load, using fallback');
            setTimeout(() => this.hideLoadingScreen(), 3000);
        });

        // 비디오가 5초 내에 시작되지 않으면 강제로 진행
        setTimeout(() => {
            if (!this.videoEnded) {
                this.hideLoadingScreen();
            }
        }, 5000);
    }

    hideLoadingScreen() {
        if (!this.loadingScreen) return;
        this.loadingScreen.classList.add('door-open');
        setTimeout(() => {
            this.loadingScreen.style.display = 'none';
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