"""Admin panel for core models"""
import threading
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Sum, Q
from django.utils import timezone as django_timezone
from datetime import timedelta

from .models import (
    TelegramUser, SearchHistory, DownloadHistory,
    ShazamLog, Broadcast, BotSettings
)


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    """Bot settings admin - singleton"""
    list_display = ('is_bot_enabled', 'max_file_size_mb', 'rate_limit_per_minute', 'is_maintenance_mode')
    fieldsets = (
        ('Bot holati', {
            'fields': ('is_bot_enabled', 'is_maintenance_mode', 'maintenance_message'),
        }),
        ('Bot sozlamalari', {
            'fields': ('bot_token', 'max_file_size_mb', 'rate_limit_per_minute'),
        }),
    )

    def has_add_permission(self, request):
        # Faqat bitta instance bo'lishi kerak
        return not BotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'last_name', 'download_count', 'is_premium', 'is_banned', 'created_at', 'last_active')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    list_filter = ('is_premium', 'is_banned', 'created_at', 'last_active')
    readonly_fields = ('telegram_id', 'created_at', 'last_active')
    actions = ['ban_users', 'unban_users', 'make_premium', 'remove_premium']

    @admin.action(description='Tanlangan foydalanuvchilarni bloklash')
    def ban_users(self, request, queryset):
        queryset.update(is_banned=True)
        self.message_user(request, f'{queryset.count()} ta foydalanuvchi bloklandi.')

    @admin.action(description='Tanlangan foydalanuvchilarni blokdan olib tashlash')
    def unban_users(self, request, queryset):
        queryset.update(is_banned=False)
        self.message_user(request, f'{queryset.count()} ta foydalanuvchi blokdan olindi.')

    @admin.action(description='Tanlangan foydalanuvchilarga premium berish')
    def make_premium(self, request, queryset):
        queryset.update(is_premium=True)
        self.message_user(request, f'{queryset.count()} ta foydalanuvchiga premium berildi.')

    @admin.action(description='Tanlangan foydalanuvchilardan premium olib tashlash')
    def remove_premium(self, request, queryset):
        queryset.update(is_premium=False)
        self.message_user(request, f'{queryset.count()} ta foydalanuvchidan premium olindi.')


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'query', 'results_count', 'searched_at')
    search_fields = ('query', 'user__username', 'user__first_name')
    list_filter = ('searched_at',)
    readonly_fields = ('searched_at',)


@admin.register(DownloadHistory)
class DownloadHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'video_title', 'platform', 'format_label', 'status', 'file_size_display', 'downloaded_at')
    search_fields = ('video_title', 'video_url', 'user__username', 'user__first_name')
    list_filter = ('platform', 'format_label', 'status', 'downloaded_at')
    readonly_fields = ('downloaded_at', 'completed_at')
    
    def file_size_display(self, obj):
        if obj.file_size:
            mb = obj.file_size / (1024 * 1024)
            return f'{mb:.2f} MB'
        return '-'
    file_size_display.short_description = 'Fayl hajmi'


@admin.register(ShazamLog)
class ShazamLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'recognized_title', 'recognized_artist', 'is_successful', 'recognized_at')
    search_fields = ('recognized_title', 'recognized_artist', 'user__username')
    list_filter = ('is_successful', 'recognized_at')
    readonly_fields = ('recognized_at',)


def send_broadcast_async(broadcast_id):
    """Send broadcast asynchronously"""
    from django.conf import settings
    import httpx

    broadcast = Broadcast.objects.get(pk=broadcast_id)
    token = settings.TELEGRAM_BOT_TOKEN
    
    # Try to get from BotSettings
    try:
        bot_settings = BotSettings.get_settings()
        if bot_settings.bot_token:
            token = bot_settings.bot_token
    except:
        pass
    
    if not token:
        broadcast.status = 'failed'
        broadcast.save()
        return

    broadcast.status = 'sending'
    broadcast.save()

    users = TelegramUser.objects.filter(is_banned=False)
    sent = 0
    failed = 0

    for user in users:
        try:
            if broadcast.photo:
                url = f'https://api.telegram.org/bot{token}/sendPhoto'
                with open(broadcast.photo.path, 'rb') as photo_file:
                    response = httpx.post(
                        url,
                        data={'chat_id': user.telegram_id, 'caption': broadcast.message, 'parse_mode': 'HTML'},
                        files={'photo': photo_file},
                        timeout=30,
                    )
            else:
                url = f'https://api.telegram.org/bot{token}/sendMessage'
                response = httpx.post(
                    url,
                    json={'chat_id': user.telegram_id, 'text': broadcast.message, 'parse_mode': 'HTML'},
                    timeout=30,
                )
            if response.status_code == 200 and response.json().get('ok'):
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


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_message', 'send_type', 'repeat_hours', 'is_active', 'status', 'sent_count', 'failed_count', 'last_sent_at', 'created_at')
    list_filter = ('status', 'send_type', 'is_active', 'created_at')
    search_fields = ('message',)
    readonly_fields = ('status', 'sent_count', 'failed_count', 'last_sent_at', 'created_at')
    actions = ['send_now']
    fieldsets = (
        ('Xabar', {
            'fields': ('message', 'photo'),
        }),
        ('Yuborish sozlamalari', {
            'fields': ('send_type', 'repeat_hours', 'is_active'),
        }),
        ('Statistika', {
            'fields': ('status', 'sent_count', 'failed_count', 'last_sent_at', 'created_at'),
        }),
    )

    def short_message(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    short_message.short_description = 'Xabar'

    @admin.action(description='Tanlangan reklamalarni hozir yuborish')
    def send_now(self, request, queryset):
        for broadcast in queryset:
            thread = threading.Thread(target=send_broadcast_async, args=(broadcast.pk,), daemon=True)
            thread.start()
        self.message_user(request, f'{queryset.count()} ta reklama yuborilmoqda...')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and obj.status == 'pending':
            thread = threading.Thread(target=send_broadcast_async, args=(obj.pk,), daemon=True)
            thread.start()


# Analytics Views
class AnalyticsAdmin(admin.ModelAdmin):
    """Analytics dashboard"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('analytics/', self.admin_site.admin_view(self.analytics_view), name='analytics'),
        ]
        return custom_urls + urls

    def analytics_view(self, request):
        """Analytics dashboard view"""
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


# Analytics will be accessible via custom admin view
