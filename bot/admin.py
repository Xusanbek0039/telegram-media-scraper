import asyncio
import threading
from django.contrib import admin
from django.utils import timezone
from .models import TelegramUser, SearchHistory, DownloadHistory, Broadcast


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'last_name', 'created_at', 'last_active')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    list_filter = ('created_at', 'last_active')
    readonly_fields = ('telegram_id', 'created_at', 'last_active')


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'query', 'results_count', 'searched_at')
    search_fields = ('query', 'user__username', 'user__first_name')
    list_filter = ('searched_at',)
    readonly_fields = ('searched_at',)


@admin.register(DownloadHistory)
class DownloadHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'video_title', 'format_label', 'video_url', 'downloaded_at')
    search_fields = ('video_title', 'video_url', 'user__username', 'user__first_name')
    list_filter = ('format_label', 'downloaded_at')
    readonly_fields = ('downloaded_at',)


def send_broadcast_async(broadcast_id):
    from django.conf import settings
    import httpx

    broadcast = Broadcast.objects.get(pk=broadcast_id)
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        broadcast.status = 'failed'
        broadcast.save()
        return

    broadcast.status = 'sending'
    broadcast.save()

    users = TelegramUser.objects.all()
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
