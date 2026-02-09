from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.db.models import Count
from django.utils import timezone as django_timezone
from datetime import timedelta

from core.models import DownloadHistory, TelegramUser, SearchHistory, ShazamLog


def analytics_view(request):
    """Analytics dashboard view"""
    if not request.user.is_staff:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    
    # Platform statistics
    platform_stats = DownloadHistory.objects.values('platform').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Daily downloads (last 30 days)
    today = django_timezone.now().date()
    daily_downloads = []
    for i in range(30):
        date = today - timedelta(days=i)
        count = DownloadHistory.objects.filter(
            downloaded_at__date=date
        ).count()
        daily_downloads.append({'date': date, 'count': count})
    daily_downloads.reverse()
    
    # Total statistics
    total_users = TelegramUser.objects.count()
    total_downloads = DownloadHistory.objects.count()
    total_searches = SearchHistory.objects.count()
    total_shazam = ShazamLog.objects.count()
    successful_shazam = ShazamLog.objects.filter(is_successful=True).count()
    
    # Recent errors
    recent_errors = DownloadHistory.objects.filter(
        status='failed'
    ).order_by('-downloaded_at')[:10]
    
    # Most active users
    active_users = TelegramUser.objects.annotate(
        download_count_total=Count('downloads')
    ).order_by('-download_count_total')[:10]
    
    context = {
        'platform_stats': platform_stats,
        'daily_downloads': daily_downloads,
        'total_users': total_users,
        'total_downloads': total_downloads,
        'total_searches': total_searches,
        'total_shazam': total_shazam,
        'successful_shazam': successful_shazam,
        'recent_errors': recent_errors,
        'active_users': active_users,
    }
    
    return render(request, 'admin/analytics.html', context)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/analytics/', analytics_view, name='admin_analytics'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
