/**
 * Django Admin 드래그 앤 드롭 정렬 + 복제 스크립트
 * MenuItem 및 Category changelist 뷰에서 작동합니다.
 * 항상 드래그 정렬 가능 상태입니다.
 */
(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const resultTable = document.querySelector('#result_list');
        if (!resultTable) return;

        const tbody = resultTable.querySelector('tbody');
        if (!tbody) return;

        const isMenuItem = window.location.pathname.includes('/menu/menuitem/');
        const isCategory = window.location.pathname.includes('/menu/category/');
        if (!isMenuItem && !isCategory) return;

        // ─────────────────────────────────────────────
        // 1. 각 행에 드래그 핸들 + 복제 링크 추가
        // ─────────────────────────────────────────────
        const rows = tbody.querySelectorAll('tr');

        // 헤더에 빈 셀 추가
        const headerRow = resultTable.querySelector('thead tr');
        if (headerRow) {
            const handleHeader = document.createElement('th');
            handleHeader.style.cssText = 'width: 30px;';
            handleHeader.innerHTML = '<span style="color:#999; font-size:11px;"></span>';
            headerRow.insertBefore(handleHeader, headerRow.firstChild);

            if (isMenuItem) {
                const actionHeader = document.createElement('th');
                actionHeader.style.cssText = 'font-size: 12px; white-space: nowrap;';
                headerRow.appendChild(actionHeader);
            }
        }

        rows.forEach(function(row) {
            // 드래그 핸들 셀
            const handleCell = document.createElement('td');
            handleCell.innerHTML = '<span class="drag-handle" title="드래그하여 순서 변경">⋮⋮</span>';
            handleCell.style.cssText = 'width: 30px; text-align: center;';
            row.insertBefore(handleCell, row.firstChild);

            // 항상 드래그 가능
            row.draggable = true;
            row.style.cursor = 'grab';

            // 복제 링크 (MenuItem만)
            if (isMenuItem) {
                const checkbox = row.querySelector('input.action-select');
                if (!checkbox) return;
                const objId = checkbox.value;

                const actionCell = document.createElement('td');
                actionCell.innerHTML = `<a href="#" class="btn-duplicate" data-id="${objId}" title="복제">복제</a>`;
                row.appendChild(actionCell);
            }
        });

        // ─────────────────────────────────────────────
        // 1.5 카테고리별 그룹화 및 헤더 추가 (MenuItem만)
        // ─────────────────────────────────────────────
        if (isMenuItem) {
            const categoryHeader = resultTable.querySelector('thead th.column-category');
            if (categoryHeader) {
                const categoryColIndex = Array.from(categoryHeader.parentNode.children).indexOf(categoryHeader);
                const groups = {};
                const noCategoryKey = '카테고리 없음';
                
                rows.forEach(function(row) {
                    const cell = row.children[categoryColIndex];
                    const catName = cell ? (cell.textContent.trim() || noCategoryKey) : noCategoryKey;
                    if (!groups[catName]) {
                        groups[catName] = [];
                    }
                    groups[catName].push(row);
                });
                
                tbody.innerHTML = '';
                
                Object.keys(groups).forEach(function(catName) {
                    const groupRows = groups[catName];
                    const headerRow = document.createElement('tr');
                    headerRow.className = 'category-group-row';
                    headerRow.style.cssText = 'background: #1e293b !important; pointer-events: none;';
                    
                    const colCount = resultTable.querySelectorAll('thead th').length;
                    
                    headerRow.innerHTML = `
                        <td colspan="${colCount}" style="
                            padding: 12px 16px;
                            font-size: 13px;
                            font-weight: 700;
                            color: #f8fafc;
                            background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
                            border-bottom: 2px solid #334155;
                            text-align: left;
                        ">📁 ${catName}</td>
                    `;
                    tbody.appendChild(headerRow);
                    
                    groupRows.forEach(function(row) {
                        tbody.appendChild(row);
                    });
                });
            }
        }

        // ─────────────────────────────────────────────
        // 2. 드래그 앤 드롭
        // ─────────────────────────────────────────────
        let dragSrcRow = null;

        tbody.querySelectorAll('tr:not(.category-group-row)').forEach(function(row) {
            row.addEventListener('dragstart', function(e) {
                dragSrcRow = this;
                this.style.opacity = '0.35';
                this.style.cursor = 'grabbing';
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', '');
            });

            row.addEventListener('dragover', function(e) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
            });

            row.addEventListener('dragenter', function() {
                this.classList.add('drag-over');
            });

            row.addEventListener('dragleave', function() {
                this.classList.remove('drag-over');
            });

            row.addEventListener('drop', function(e) {
                e.stopPropagation();
                this.classList.remove('drag-over');
                if (dragSrcRow && dragSrcRow !== this) {
                    // 동일 카테고리 그룹 내에서만 드래그앤드롭 허용하여 카테고리 이탈 방지
                    const allRows = Array.from(tbody.querySelectorAll('tr'));
                    const srcIdx = allRows.indexOf(dragSrcRow);
                    const dstIdx = allRows.indexOf(this);
                    
                    if (srcIdx < dstIdx) {
                        tbody.insertBefore(dragSrcRow, this.nextSibling);
                    } else {
                        tbody.insertBefore(dragSrcRow, this);
                    }
                    saveOrder();
                }
            });

            row.addEventListener('dragend', function() {
                this.style.opacity = '1';
                this.style.cursor = 'grab';
                tbody.querySelectorAll('tr').forEach(function(r) {
                    r.classList.remove('drag-over');
                });
            });
        });

        // ─────────────────────────────────────────────
        // 3. 순서 저장 (AJAX)
        // ─────────────────────────────────────────────
        function saveOrder() {
            const currentRows = tbody.querySelectorAll('tr:not(.category-group-row)');
            const ids = [];
            currentRows.forEach(function(row) {
                const cb = row.querySelector('input.action-select');
                if (cb) ids.push(parseInt(cb.value));
            });

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || getCookie('csrftoken');

            const endpoint = isMenuItem
                ? '/admin/menu/menuitem/reorder/'
                : '/admin/menu/category/reorder/';

            fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({ ids: ids }),
            })
            .then(function(res) { return res.json(); })
            .then(function() {
                showToast('순서가 저장되었습니다');
            })
            .catch(function(err) {
                showToast('순서 저장 실패: ' + err.message, true);
            });
        }

        // ─────────────────────────────────────────────
        // 4. 복제 핸들러
        // ─────────────────────────────────────────────
        document.querySelectorAll('.btn-duplicate').forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const menuId = this.dataset.id;
                if (!confirm('이 메뉴를 복제하시겠습니까?')) return;

                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                    || getCookie('csrftoken');

                fetch('/admin/menu/menuitem/' + menuId + '/duplicate/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                })
                .then(function(res) { return res.json(); })
                .then(function(data) {
                    if (data.status === 'success') {
                        window.location.reload();
                    } else {
                        alert('복제 실패: ' + (data.message || '알 수 없는 오류'));
                    }
                })
                .catch(function(err) {
                    alert('복제 요청 실패: ' + err.message);
                });
            });
        });

        // ─────────────────────────────────────────────
        // 5. 토스트 알림
        // ─────────────────────────────────────────────
        function showToast(msg, isError) {
            let toast = document.getElementById('sort-toast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'sort-toast';
                document.body.appendChild(toast);
            }
            toast.textContent = msg;
            toast.style.cssText = `
                position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
                padding: 10px 24px; border-radius: 8px; font-size: 13px; font-weight: 600;
                color: #fff; z-index: 99999; opacity: 0;
                transition: opacity 0.3s ease;
                background: ${isError ? '#ef4444' : '#417690'};
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            `;
            requestAnimationFrame(function() {
                toast.style.opacity = '1';
            });
            setTimeout(function() {
                toast.style.opacity = '0';
            }, 1800);
        }

        // ─────────────────────────────────────────────
        // 6. 스타일
        // ─────────────────────────────────────────────
        const style = document.createElement('style');
        style.textContent = `
            .drag-handle {
                cursor: grab;
                font-size: 16px;
                color: #999;
                user-select: none;
                letter-spacing: 1px;
            }
            .drag-handle:hover { color: #417690; }
            #result_list tbody tr {
                transition: background 0.12s ease, opacity 0.15s ease;
            }
            #result_list tbody tr:hover .drag-handle { color: #417690; }
            #result_list tbody tr.drag-over {
                background: #e8f0fe !important;
                box-shadow: inset 0 -2px 0 0 #417690;
            }
            .btn-duplicate {
                color: #417690 !important;
                font-size: 12px;
                text-decoration: none !important;
                white-space: nowrap;
            }
            .btn-duplicate:hover {
                color: #205067 !important;
                text-decoration: underline !important;
            }
        `;
        document.head.appendChild(style);
    });

    function getCookie(name) {
        let v = null;
        if (document.cookie) {
            document.cookie.split(';').forEach(function(c) {
                c = c.trim();
                if (c.startsWith(name + '=')) {
                    v = decodeURIComponent(c.substring(name.length + 1));
                }
            });
        }
        return v;
    }
})();
