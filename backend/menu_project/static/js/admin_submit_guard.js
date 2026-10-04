/* 관리 화면 이중 제출 가드.
 *
 * 왜 있는가 — 2026-09-30 새벽, bid 사장님이 카테고리 "PNN" 을 3개, 메뉴
 * "MENU" 를 2개 만들었다가 손으로 지웠다. 같은 초의 서버 로그에 uwsgi 의
 * write error (Broken pipe) 가 남아 있었다. 저장은 커밋됐는데(관리 로그에
 * 3건 다 있다) 응답이 브라우저에 닿지 못해 화면이 그대로였고, 반응이 없으니
 * 또 누른 것이다. /admin/menu/category/add/?_popup=1 에 nginx 499(클라이언트가
 * 끊음)가 8건 쌓여 있었으니 그날 한 번이 아니다.
 *
 * 그래서 첫 제출만 통과시키고 나머지는 삼킨다.
 *
 * 왜 disabled 를 쓰지 않는가 — 제출 핸들러 안에서 버튼을 disabled 로 만들면
 * 브라우저가 그 버튼을 폼 데이터에서 빼 버린다. Django admin 은
 * `_save` / `_continue` / `_addanother` / `_saveasnew` 라는 **버튼 이름**이
 * POST 에 들어왔는지로 다음 화면을 정한다. 즉 흔한 방식으로 가드를 넣는
 * 순간 "저장하고 계속 편집" 이 조용히 "저장" 으로 바뀐다. 저장은 되고
 * 이동만 틀리는 종류라서 한참 못 알아챈다. 값과 name 은 건드리지 않고
 * pointer-events 로만 막는다.
 */
(function () {
    'use strict';

    var BUSY = 'submit-guard-busy';
    var NOTE = 'submit-guard-note';

    /* 느린 업로드를 기다리다 지친 사람이 아예 아무것도 못 하게 되는 쪽이
       중복보다 나쁘다. 응답이 영영 안 오면 풀어 준다. */
    var RELEASE_MS = 20000;

    function injectStyle() {
        if (document.getElementById('submit-guard-style')) return;
        var style = document.createElement('style');
        style.id = 'submit-guard-style';
        style.textContent =
            '.' + BUSY + ' input[type="submit"],' +
            '.' + BUSY + ' button[type="submit"],' +
            '.' + BUSY + ' button:not([type]) {' +
            'pointer-events:none;opacity:.55;cursor:default;}' +
            '.' + NOTE + '{' +
            'display:inline-block;margin-left:10px;font-size:13px;' +
            'font-weight:600;opacity:.75;vertical-align:middle;}';
        (document.head || document.documentElement).appendChild(style);
    }

    function showNote(form, submitter) {
        if (form.querySelector('.' + NOTE)) return;
        var note = document.createElement('span');
        note.className = NOTE;
        note.setAttribute('aria-live', 'polite');
        note.textContent = '저장 중…';
        /* 누른 버튼 바로 옆에 붙인다. 긴 폼에서 화면 밖에 떠 있는 안내는
           안 읽힌다 — 그게 애초에 이 버그의 원인이다. */
        if (submitter && submitter.parentNode) {
            submitter.parentNode.insertBefore(note, submitter.nextSibling);
        } else {
            var row = form.querySelector('.submit-row') || form;
            row.appendChild(note);
        }
    }

    function guard(form) {
        if (form.dataset.submitGuard === '1') return;
        form.dataset.submitGuard = '1';

        form.addEventListener('submit', function (event) {
            /* 인라인 onsubmit 이 먼저 돈다. billing.html 의 해지 폼은
               `onsubmit="return confirm(...)"` 이라서, 사장님이 "취소" 를
               누르면 제출이 막힌 채로 이 핸들러까지 온다. 그걸 저장으로
               세면 아무것도 안 보낸 폼이 20초간 잠긴다. */
            if (event.defaultPrevented) return;

            if (form.classList.contains(BUSY)) {
                /* 두 번째 이후. 첫 제출이 아직 날아가는 중이다. */
                event.preventDefault();
                event.stopImmediatePropagation();
                return;
            }
            form.classList.add(BUSY);
            injectStyle();
            showNote(form, event.submitter || null);

            window.setTimeout(function () {
                form.classList.remove(BUSY);
                var note = form.querySelector('.' + NOTE);
                if (note && note.parentNode) note.parentNode.removeChild(note);
            }, RELEASE_MS);
        });
    }

    function init() {
        /* GET 폼(검색·필터)은 건드리지 않는다. 중복으로 생기는 게 없고,
           막아 두면 검색어를 고쳐 다시 누르는 게 안 된다. */
        var forms = document.querySelectorAll('form[method="post"], form[method="POST"]');
        for (var i = 0; i < forms.length; i++) guard(forms[i]);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
