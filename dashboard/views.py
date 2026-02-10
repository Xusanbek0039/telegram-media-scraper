import threading
import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Count, Q, Sum, Avg, F
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from django.conf import settings
import httpx

from core.models import (
    TelegramUser, DownloadHistory, ShazamLog, Broadcast, BotSettings,
    SearchHistory, AdCampaign, PremiumPlan, ReferralStats, ErrorLog,
)


LOGIN_URL = 'dashboard:login'


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
        messages.error(request, "Login yoki parol noto'g'ri.")
    return render(request, 'dashboard/login.html')


@login_required(login_url=LOGIN_URL)
def logout_view(request):
    logout(request)
    messages.success(request, 'Chiqdingiz.')
    return redirect('dashboard:login')


# ─── 1. DASHBOARD ───────────────────────────────────────────
@login_required(login_url=LOGIN_URL)
def home_view(request):
    now = timezone.now()
    today = now.date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

    total_users = TelegramUser.objects.count()
    today_users = TelegramUser.objects.filter(created_at__date=today).count()
    active_users = TelegramUser.objects.filter(last_active__gte=now - timedelta(hours=24)).count()
    premium_users = TelegramUser.objects.filter(is_premium=True).count()

    total_downloads = DownloadHistory.objects.count()
    today_downloads = DownloadHistory.objects.filter(downloaded_at__date=today).count()
    failed_downloads = DownloadHistory.objects.filter(status='failed', downloaded_at__date=today).count()

    total_shazam = ShazamLog.objects.count()
    today_shazam = ShazamLog.objects.filter(recognized_at__date=today).count()

    today_errors = DownloadHistory.objects.filter(status='failed', downloaded_at__date=today).count()
    try:
        today_errors += ErrorLog.objects.filter(created_at__date=today).count()
    except Exception:
        pass

    daily_data = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        dl_count = DownloadHistory.objects.filter(downloaded_at__date=d).count()
        user_count = TelegramUser.objects.filter(created_at__date=d).count()
        daily_data.append({
            'date': d.strftime('%d.%m'),
            'downloads': dl_count,
            'users': user_count,
        })

    platform_stats = list(
        DownloadHistory.objects.values('platform')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    features = [
        {'name': 'Video yuklash', 'count': total_downloads},
        {'name': 'Shazam', 'count': total_shazam},
        {'name': 'Qidiruv', 'count': SearchHistory.objects.count()},
    ]
    features.sort(key=lambda x: x['count'], reverse=True)

    recent_downloads = DownloadHistory.objects.select_related('user').order_by('-downloaded_at')[:10]

    context = {
        'total_users': total_users,
        'today_users': today_users,
        'active_users': active_users,
        'premium_users': premium_users,
        'total_downloads': total_downloads,
        'today_downloads': today_downloads,
        'failed_downloads': failed_downloads,
        'total_shazam': total_shazam,
        'today_shazam': today_shazam,
        'today_errors': today_errors,
        'daily_data': json.dumps(daily_data),
        'platform_stats': json.dumps(platform_stats),
        'features': features,
        'recent_downloads': recent_downloads,
    }
    return render(request, 'dashboard/home.html', context)


# ─── 2. USERS ───────────────────────────────────────────────
@login_required(login_url=LOGIN_URL)
def users_view(request):
    search = request.GET.get('q', '').strip()
    filter_type = request.GET.get('filter', 'all')

    users = TelegramUser.objects.annotate(
        downloads_count=Count('downloads'),
        shazam_count=Count('shazam_logs'),
    )

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(telegram_id__icontains=search)
        )

    if filter_type == 'premium':
        users = users.filter(is_premium=True)
    elif filter_type == 'banned':
        users = users.filter(is_banned=True)
    elif filter_type == 'active':
        users = users.filter(last_active__gte=timezone.now() - timedelta(hours=24))

    users = users.order_by('-last_active')

    context = {
        'users': users,
        'search': search,
        'filter_type': filter_type,
        'total_count': TelegramUser.objects.count(),
        'premium_count': TelegramUser.objects.filter(is_premium=True).count(),
        'banned_count': TelegramUser.objects.filter(is_banned=True).count(),
    }
    return render(request, 'dashboard/users.html', context)


@login_required(login_url=LOGIN_URL)
@require_POST
def user_toggle_premium(request, pk):
    user = get_object_or_404(TelegramUser, pk=pk)
    user.is_premium = not user.is_premium
    user.save(update_fields=['is_premium'])
    return JsonResponse({'ok': True, 'is_premium': user.is_premium})


@login_required(login_url=LOGIN_URL)
@require_POST
def user_toggle_ban(request, pk):
    user = get_object_or_404(TelegramUser, pk=pk)
    user.is_banned = not user.is_banned
    user.save(update_fields=['is_banned'])
    return JsonResponse({'ok': True, 'is_banned': user.is_banned})


@login_required(login_url=LOGIN_URL)
def user_detail_view(request, pk):
    user = get_object_or_404(TelegramUser, pk=pk)
    downloads = DownloadHistory.objects.filter(user=user).order_by('-downloaded_at')[:50]
    shazam_logs = ShazamLog.objects.filter(user=user).order_by('-recognized_at')[:50]

    total_downloads = DownloadHistory.objects.filter(user=user).count()
    successful_downloads = DownloadHistory.objects.filter(user=user, status='completed').count()
    total_shazam = ShazamLog.objects.filter(user=user).count()
    successful_shazam = ShazamLog.objects.filter(user=user, is_successful=True).count()

    context = {
        'profile': user,
        'downloads': downloads,
        'shazam_logs': shazam_logs,
        'total_downloads': total_downloads,
        'successful_downloads': successful_downloads,
        'total_shazam': total_shazam,
        'successful_shazam': successful_shazam,
    }
    return render(request, 'dashboard/user_detail.html', context)


# ─── 3. MEDIA & MUSIC ───────────────────────────────────────
@login_required(login_url=LOGIN_URL)
def media_view(request):
    platform_filter = request.GET.get('platform', 'all')
    status_filter = request.GET.get('status', 'all')

    downloads = DownloadHistory.objects.select_related('user').order_by('-downloaded_at')

    if platform_filter != 'all':
        downloads = downloads.filter(platform=platform_filter)
    if status_filter != 'all':
        downloads = downloads.filter(status=status_filter)

    total = DownloadHistory.objects.count()
    completed = DownloadHistory.objects.filter(status='completed').count()
    failed = DownloadHistory.objects.filter(status='failed').count()
    pending = DownloadHistory.objects.filter(status__in=['pending', 'processing']).count()

    context = {
        'downloads': downloads[:100],
        'platform_filter': platform_filter,
        'status_filter': status_filter,
        'total': total,
        'completed': completed,
        'failed': failed,
        'pending': pending,
    }
    return render(request, 'dashboard/media.html', context)


@login_required(login_url=LOGIN_URL)
def music_view(request):
    status_filter = request.GET.get('status', 'all')

    logs = ShazamLog.objects.select_related('user').order_by('-recognized_at')

    if status_filter == 'success':
        logs = logs.filter(is_successful=True)
    elif status_filter == 'failed':
        logs = logs.filter(is_successful=False)

    total = ShazamLog.objects.count()
    successful = ShazamLog.objects.filter(is_successful=True).count()
    failed_count = ShazamLog.objects.filter(is_successful=False).count()
    success_rate = round(successful / total * 100, 1) if total > 0 else 0

    context = {
        'logs': logs[:100],
        'status_filter': status_filter,
        'total': total,
        'successful': successful,
        'failed_count': failed_count,
        'success_rate': success_rate,
    }
    return render(request, 'dashboard/music.html', context)


# ─── 4. ADS & MARKETING ─────────────────────────────────────
@login_required(login_url=LOGIN_URL)
def ads_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            campaign = AdCampaign.objects.create(
                name=request.POST.get('name', ''),
                message=request.POST.get('message', ''),
                button_text=request.POST.get('button_text', ''),
                button_url=request.POST.get('button_url', ''),
                target_audience=request.POST.get('target_audience', 'all'),
                scheduled_at=request.POST.get('scheduled_at') or None,
                status='draft',
            )
            messages.success(request, f'Kampaniya "{campaign.name}" yaratildi.')
            return redirect('dashboard:ads')
        elif action == 'send':
            campaign_id = request.POST.get('campaign_id')
            campaign = get_object_or_404(AdCampaign, pk=campaign_id)
            thread = threading.Thread(target=_send_campaign, args=(campaign.pk,), daemon=True)
            thread.start()
            messages.success(request, f'Kampaniya "{campaign.name}" yuborilmoqda...')
            return redirect('dashboard:ads')
        elif action == 'delete':
            campaign_id = request.POST.get('campaign_id')
            campaign = get_object_or_404(AdCampaign, pk=campaign_id)
            campaign.delete()
            messages.success(request, 'Kampaniya oʻchirildi.')
            return redirect('dashboard:ads')

    campaigns = AdCampaign.objects.order_by('-created_at')[:30]
    context = {'campaigns': campaigns}
    return render(request, 'dashboard/ads.html', context)


@login_required(login_url=LOGIN_URL)
def broadcast_view(request):
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        target = request.POST.get('target', 'all')
        if not message_text:
            messages.error(request, 'Xabar matnini kiriting.')
            return redirect('dashboard:broadcast')
        broadcast = Broadcast.objects.create(
            message=message_text,
            status='pending',
        )
        thread = threading.Thread(target=_send_broadcast, args=(broadcast.pk, target), daemon=True)
        thread.start()
        messages.success(request, 'Reklama yuborilmoqda...')
        return redirect('dashboard:broadcast')
    broadcasts = Broadcast.objects.order_by('-created_at')[:20]
    total_users = TelegramUser.objects.filter(is_banned=False).count()
    premium_users = TelegramUser.objects.filter(is_banned=False, is_premium=True).count()
    free_users = TelegramUser.objects.filter(is_banned=False, is_premium=False).count()
    return render(request, 'dashboard/broadcast.html', {
        'broadcasts': broadcasts,
        'total_users': total_users,
        'premium_users': premium_users,
        'free_users': free_users,
    })


def _send_broadcast(broadcast_id, target='all'):
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
    if target == 'premium':
        users = users.filter(is_premium=True)
    elif target == 'free':
        users = users.filter(is_premium=False)
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


def _send_campaign(campaign_id):
    campaign = AdCampaign.objects.get(pk=campaign_id)
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    try:
        bot_settings = BotSettings.get_settings()
        if bot_settings.bot_token:
            token = bot_settings.bot_token
    except Exception:
        pass
    if not token:
        campaign.status = 'failed'
        campaign.save()
        return
    campaign.status = 'sending'
    campaign.save()
    users = TelegramUser.objects.filter(is_banned=False)
    if campaign.target_audience == 'premium':
        users = users.filter(is_premium=True)
    elif campaign.target_audience == 'free':
        users = users.filter(is_premium=False)
    sent = failed = 0
    for u in users:
        try:
            payload = {
                'chat_id': u.telegram_id,
                'text': campaign.message,
                'parse_mode': 'HTML',
            }
            if campaign.button_text and campaign.button_url:
                payload['reply_markup'] = json.dumps({
                    'inline_keyboard': [[{
                        'text': campaign.button_text,
                        'url': campaign.button_url,
                    }]]
                })
            r = httpx.post(
                f'https://api.telegram.org/bot{token}/sendMessage',
                json=payload,
                timeout=30,
            )
            if r.status_code == 200 and r.json().get('ok'):
                sent += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    campaign.sent_count = sent
    campaign.failed_count = failed
    campaign.status = 'sent'
    campaign.save()


# ─── 5. PREMIUM / MONETIZATION ──────────────────────────────
@login_required(login_url=LOGIN_URL)
def premium_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            PremiumPlan.objects.create(
                name=request.POST.get('name', ''),
                description=request.POST.get('description', ''),
                price=request.POST.get('price', 0),
                duration_days=request.POST.get('duration_days', 30),
                daily_download_limit=request.POST.get('daily_download_limit', 100),
                daily_shazam_limit=request.POST.get('daily_shazam_limit', 50),
                max_file_size_mb=request.POST.get('max_file_size_mb', 100),
            )
            messages.success(request, 'Tarif yaratildi.')
            return redirect('dashboard:premium')
        elif action == 'toggle':
            plan_id = request.POST.get('plan_id')
            plan = get_object_or_404(PremiumPlan, pk=plan_id)
            plan.is_active = not plan.is_active
            plan.save(update_fields=['is_active'])
            return JsonResponse({'ok': True, 'is_active': plan.is_active})
        elif action == 'delete':
            plan_id = request.POST.get('plan_id')
            plan = get_object_or_404(PremiumPlan, pk=plan_id)
            plan.delete()
            messages.success(request, 'Tarif oʻchirildi.')
            return redirect('dashboard:premium')

    plans = PremiumPlan.objects.order_by('-is_active', 'price')
    premium_users = TelegramUser.objects.filter(is_premium=True).count()
    free_users = TelegramUser.objects.filter(is_premium=False).count()
    total_referrals = ReferralStats.objects.count()
    rewarded_referrals = ReferralStats.objects.filter(is_rewarded=True).count()

    context = {
        'plans': plans,
        'premium_users': premium_users,
        'free_users': free_users,
        'total_referrals': total_referrals,
        'rewarded_referrals': rewarded_referrals,
    }
    return render(request, 'dashboard/premium.html', context)


# ─── 6. BOT SETTINGS ────────────────────────────────────────
@login_required(login_url=LOGIN_URL)
def settings_view(request):
    bot_settings = BotSettings.get_settings()

    if request.method == 'POST':
        section = request.POST.get('section', 'general')

        if section == 'general':
            bot_settings.is_bot_enabled = request.POST.get('is_bot_enabled') == 'on'
            bot_settings.is_maintenance_mode = request.POST.get('is_maintenance_mode') == 'on'
            bot_settings.rate_limit_per_minute = int(request.POST.get('rate_limit_per_minute', 10))
            bot_settings.max_file_size_mb = int(request.POST.get('max_file_size_mb', 50))
            bot_settings.maintenance_message = request.POST.get('maintenance_message', '')
        elif section == 'downloader':
            bot_settings.youtube_enabled = request.POST.get('youtube_enabled') == 'on'
            bot_settings.instagram_enabled = request.POST.get('instagram_enabled') == 'on'
            bot_settings.tiktok_enabled = request.POST.get('tiktok_enabled') == 'on'
            bot_settings.snapchat_enabled = request.POST.get('snapchat_enabled') == 'on'
            bot_settings.likee_enabled = request.POST.get('likee_enabled') == 'on'
            bot_settings.parallel_download_limit = int(request.POST.get('parallel_download_limit', 3))
        elif section == 'shazam':
            bot_settings.shazam_daily_limit = int(request.POST.get('shazam_daily_limit', 20))
            bot_settings.shazam_max_audio_length = int(request.POST.get('shazam_max_audio_length', 60))
        elif section == 'limits':
            bot_settings.free_daily_download_limit = int(request.POST.get('free_daily_download_limit', 5))
            bot_settings.premium_daily_download_limit = int(request.POST.get('premium_daily_download_limit', 100))

        bot_settings.save()
        messages.success(request, 'Sozlamalar saqlandi.')
        return redirect('dashboard:settings')

    context = {'bot_settings': bot_settings}
    return render(request, 'dashboard/settings.html', context)


# ─── 7. ANALYTICS ───────────────────────────────────────────
@login_required(login_url=LOGIN_URL)
def analytics_view(request):
    today = timezone.now().date()

    platform_stats = list(
        DownloadHistory.objects.values('platform')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    hourly_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        for h in range(24):
            count = DownloadHistory.objects.filter(
                downloaded_at__date=d,
                downloaded_at__hour=h,
            ).count()
            if count > 0:
                hourly_data.append({'day': d.strftime('%a'), 'hour': h, 'count': count})

    daily_downloads = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        count = DownloadHistory.objects.filter(downloaded_at__date=d).count()
        daily_downloads.append({'date': d.strftime('%d.%m'), 'count': count})

    daily_users = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        count = TelegramUser.objects.filter(created_at__date=d).count()
        daily_users.append({'date': d.strftime('%d.%m'), 'count': count})

    active_users = TelegramUser.objects.annotate(
        total_downloads=Count('downloads'),
    ).order_by('-total_downloads')[:10]

    total_dl = DownloadHistory.objects.count()
    success_dl = DownloadHistory.objects.filter(status='completed').count()
    total_shazam = ShazamLog.objects.count()
    success_shazam = ShazamLog.objects.filter(is_successful=True).count()

    context = {
        'platform_stats': json.dumps(platform_stats),
        'hourly_data': json.dumps(hourly_data),
        'daily_downloads': json.dumps(daily_downloads),
        'daily_users': json.dumps(daily_users),
        'active_users': active_users,
        'total_dl': total_dl,
        'success_dl': success_dl,
        'dl_rate': round(success_dl / total_dl * 100, 1) if total_dl > 0 else 0,
        'total_shazam': total_shazam,
        'success_shazam': success_shazam,
        'shazam_rate': round(success_shazam / total_shazam * 100, 1) if total_shazam > 0 else 0,
    }
    return render(request, 'dashboard/analytics.html', context)


# ─── 8. LOGS & MONITORING ───────────────────────────────────
@login_required(login_url=LOGIN_URL)
def logs_view(request):
    log_type = request.GET.get('type', 'all')

    try:
        error_logs = ErrorLog.objects.order_by('-created_at')
        if log_type != 'all':
            error_logs = error_logs.filter(error_type=log_type)
        error_logs = error_logs[:100]
        error_log_exists = True
    except Exception:
        error_logs = []
        error_log_exists = False

    download_errors = DownloadHistory.objects.filter(
        status='failed'
    ).select_related('user').order_by('-downloaded_at')[:50]

    shazam_fails = ShazamLog.objects.filter(
        is_successful=False
    ).select_related('user').order_by('-recognized_at')[:50]

    today = timezone.now().date()
    today_download_errors = DownloadHistory.objects.filter(status='failed', downloaded_at__date=today).count()
    today_shazam_fails = ShazamLog.objects.filter(is_successful=False, recognized_at__date=today).count()
    try:
        today_system_errors = ErrorLog.objects.filter(created_at__date=today).count()
    except Exception:
        today_system_errors = 0

    context = {
        'error_logs': error_logs,
        'error_log_exists': error_log_exists,
        'download_errors': download_errors,
        'shazam_fails': shazam_fails,
        'log_type': log_type,
        'today_download_errors': today_download_errors,
        'today_shazam_fails': today_shazam_fails,
        'today_system_errors': today_system_errors,
    }
    return render(request, 'dashboard/logs.html', context)


@login_required(login_url=LOGIN_URL)
@require_POST
def resolve_error(request, pk):
    try:
        error = get_object_or_404(ErrorLog, pk=pk)
        error.is_resolved = not error.is_resolved
        error.save(update_fields=['is_resolved'])
        return JsonResponse({'ok': True, 'is_resolved': error.is_resolved})
    except Exception:
        return JsonResponse({'ok': False})


# ─── HISTORY (legacy, keep) ─────────────────────────────────
@login_required(login_url=LOGIN_URL)
def history_view(request):
    users_with_activity = TelegramUser.objects.annotate(
        downloads_count=Count('downloads'),
        shazam_count=Count('shazam_logs'),
    ).filter(
        Q(downloads_count__gt=0) | Q(shazam_count__gt=0)
    ).order_by('-last_active')

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


# ─── API endpoints for AJAX ─────────────────────────────────
@login_required(login_url=LOGIN_URL)
@require_GET
def api_stats(request):
    """Real-time stats endpoint for dashboard auto-refresh"""
    now = timezone.now()
    today = now.date()
    return JsonResponse({
        'total_users': TelegramUser.objects.count(),
        'active_users': TelegramUser.objects.filter(last_active__gte=now - timedelta(hours=24)).count(),
        'today_downloads': DownloadHistory.objects.filter(downloaded_at__date=today).count(),
        'today_shazam': ShazamLog.objects.filter(recognized_at__date=today).count(),
    })
