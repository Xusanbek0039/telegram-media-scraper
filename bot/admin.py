from django.contrib import admin
from .models import TelegramUser, SearchHistory


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
