"""
Legacy models - kept for backward compatibility with migrations
All models are now in core.models
"""
from core.models import (
    TelegramUser,
    SearchHistory,
    DownloadHistory,
    Broadcast,
    BotSettings,
    ShazamLog,
)

__all__ = [
    'TelegramUser',
    'SearchHistory',
    'DownloadHistory',
    'Broadcast',
    'BotSettings',
    'ShazamLog',
]
