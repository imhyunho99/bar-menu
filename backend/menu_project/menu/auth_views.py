"""
매장 주소를 몰라도 되는 로그인 · 로그아웃.

기존 로그인은 /<slug>/admin/login/ 이라 사장님이 자기 매장 주소를 외우고
있어야 들어올 수 있었다. 셀프가입으로 들어온 사람은 가입할 때 한 번 정하고
잊어버린다. 여기서는 계정으로 매장을 찾아 대신 데려다준다.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render


def _home_for(user):
    """
    로그인한 사장님이 도착할 곳. 관리할 매장이 없으면 None.

    Django admin 이 집이다. 메뉴 편집과 디자인·레이아웃 빌더가 둘 다 거기에
    있어서, 예전처럼 /<slug>/admin/dashboard/ 로 보내면 디자인을 고치려는
    사장님은 도착하자마자 다른 화면으로 건너가야 했다.

    주문·결제·QR 은 아직 /<slug>/admin/ 에 남아 있고, /admin/ 첫 화면이
    그리로 가는 바로가기를 들고 있다.
    """
    profile = getattr(user, 'profile', None)
    if (profile and profile.restaurant) or user.is_superuser:
        return redirect('admin:index')

    return None


def login_view(request):
    if request.user.is_authenticated:
        home = _home_for(request.user)
        if home:
            return home

    email = ''
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)

        if user is None or not user.is_staff:
            # 어느 쪽이 틀렸는지는 알려주지 않는다. 가입 여부가 새어나간다.
            messages.error(request, '이메일 또는 비밀번호가 올바르지 않습니다.')
        else:
            login(request, user)
            home = _home_for(user)
            if home:
                return home
            messages.error(request, '이 계정에 연결된 매장이 없습니다. 문의해 주세요.')

    return render(request, 'auth/login.html', {'email': email})


def logout_view(request):
    logout(request)
    return redirect('login')
