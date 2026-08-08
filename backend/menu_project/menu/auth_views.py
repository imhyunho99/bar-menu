"""
매장 주소를 몰라도 되는 로그인 · 로그아웃.

기존 로그인은 /<slug>/admin/login/ 이라 사장님이 자기 매장 주소를 외우고
있어야 들어올 수 있었다. 셀프가입으로 들어온 사람은 가입할 때 한 번 정하고
잊어버린다. 여기서는 계정으로 매장을 찾아 대신 데려다준다.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from .models import Restaurant


def _home_for(user):
    """이 계정이 관리하는 매장의 대시보드 주소. 없으면 None."""
    profile = getattr(user, 'profile', None)
    if profile and profile.restaurant:
        return redirect('menu:admin_dashboard', restaurant_slug=profile.restaurant.slug)

    # 슈퍼유저는 매장에 매여 있지 않다. 첫 매장으로 보낸다.
    if user.is_superuser:
        first = Restaurant.objects.order_by('id').first()
        if first:
            return redirect('menu:admin_dashboard', restaurant_slug=first.slug)

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
