import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
import httpx

from core.models import TelegramUser, DownloadHistory, ShazamLog, Broadcast, BotSettings


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        if not username or not password:
            messages.error(request, 'Login va parol kiriting.')
            return redirect('dashboard:login')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Xush kelibsiz, {user.username}!')
            next_url = request.GET.get('next', 'dashboard:home')
            return redirect(next_url)
        messages.error(request, 'Login yoki parol noto\'g\'ri.')
    return render(request, 'dashboard/login.html')


@login_required(login_url='dashboard:login')
def logout_view(request):
    logout(request)
    messages.success(request, 'Chiqdingiz.')
    return redirect('dashboard:login')


@login_required(login_url='dashboard:login')
def home_view(request):
    total_users = TelegramUser.objects.count()
    total_downloads = DownloadHistory.objects.count()
    total_shazam = ShazamLog.objects.count()
    recent_downloads = DownloadHistory.objects.select_related('user').order_by('-downloaded_at')[:15]
    context = {
        'total_users': total_users,
        'total_downloads': total_downloads,
        'total_shazam': total_shazam,
        'recent_downloads': recent_downloads,
    }
    return render(request, 'dashboard/home.html', context)


@login_required(login_url='dashboard:login')
def users_view(request):
    users = TelegramUser.objects.annotate(
        downloads_count=Count('downloads'),
        shazam_count=Count('shazam_logs'),
    ).order_by('-last_active')
    return render(request, 'dashboard/users.html', {'users': users})


@login_required(login_url='dashboard:login')
@require_POST
def user_toggle_premium(request, pk):
    user = get_object_or_404(TelegramUser, pk=pk)
    user.is_premium = not user.is_premium
    user.save(update_fields=['is_premium'])
    return JsonResponse({'ok': True, 'is_premium': user.is_premium})


@login_required(login_url='dashboard:login')
@require_POST
def user_toggle_ban(request, pk):
    user = get_object_or_404(TelegramUser, pk=pk)
    user.is_banned = not user.is_banned
    user.save(update_fields=['is_banned'])
    return JsonResponse({'ok': True, 'is_banned': user.is_banned})


@login_required(login_url='dashboard:login')
def broadcast_view(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if not message:
            messages.error(request, 'Xabar matnini kiriting.')
            return redirect('dashboard:broadcast')
        # Create and send broadcast (async)
        broadcast = Broadcast.objects.create(
            message=message,
            status='pending',
        )
        thread = threading.Thread(target=_send_broadcast, args=(broadcast.pk,), daemon=True)
        thread.start()
        messages.success(request, 'Reklama yuborilmoqda...')
        return redirect('dashboard:broadcast')
    broadcasts = Broadcast.objects.order_by('-created_at')[:20]
    return render(request, 'dashboard/broadcast.html', {'broadcasts': broadcasts})


def _send_broadcast(broadcast_id):
    broadcast = Broadcast.objects.get(pk=broadcast_id)
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    try:
        bot_settings = BotSettings.get_settings()
        if bot_settings.bot_token:
            token = bot_settings.bot_token
    except Exception:
        pass
    if not token:
        broadcast.status = 'failed'
        broadcast.save()
        return
    broadcast.status = 'sending'
    broadcast.save()
    users = TelegramUser.objects.filter(is_banned=False)
    sent = failed = 0
    for u in users:
        try:
            r = httpx.post(
                f'https://api.telegram.org/bot{token}/sendMessage',
                json={'chat_id': u.telegram_id, 'text': broadcast.message, 'parse_mode': 'HTML'},
                timeout=30,
            )
            if r.status_code == 200 and r.json().get('ok'):
                sent += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    broadcast.sent_count = sent
    broadcast.failed_count = failed
    broadcast.last_sent_at = timezone.now()
    broadcast.status = 'sent'
    broadcast.save()


@login_required(login_url='dashboard:login')
def history_view(request):
    # Group by user: each user with their downloads and shazam logs
    users_with_activity = TelegramUser.objects.annotate(
        downloads_count=Count('downloads'),
        shazam_count=Count('shazam_logs'),
    ).filter(
        Q(downloads_count__gt=0) | Q(shazam_count__gt=0)
    ).order_by('-last_active')
    
    # Optional: filter by user
    user_id = request.GET.get('user_id')
    selected_user = None
    downloads = DownloadHistory.objects.none()
    shazam_logs = ShazamLog.objects.none()
    
    if user_id:
        selected_user = get_object_or_404(TelegramUser, pk=user_id)
        downloads = DownloadHistory.objects.filter(user=selected_user).order_by('-downloaded_at')
        shazam_logs = ShazamLog.objects.filter(user=selected_user).order_by('-recognized_at')
    
    context = {
        'users_with_activity': users_with_activity,
        'selected_user': selected_user,
        'downloads': downloads,
        'shazam_logs': shazam_logs,
    }
    return render(request, 'dashboard/history.html', context)


@login_required(login_url='dashboard:login')
def user_detail_view(request, pk):
    user = get_object_or_404(TelegramUser, pk=pk)
    downloads = DownloadHistory.objects.filter(user=user).order_by('-downloaded_at')
    shazam_logs = ShazamLog.objects.filter(user=user).order_by('-recognized_at')
    return render(request, 'dashboard/user_detail.html', {
        'profile': user,
        'downloads': downloads,
        'shazam_logs': shazam_logs,
    })
