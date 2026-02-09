"""Message handlers - routes to appropriate services"""
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async

from core.models import TelegramUser, SearchHistory
from services.downloaders.factory import DownloaderFactory
from .download import handle_download_request
from .search import handle_search_request


@sync_to_async
def save_user(tg_user):
    """Save or update user in database"""
    user, _ = TelegramUser.objects.update_or_create(
        telegram_id=tg_user.id,
        defaults={
            'username': tg_user.username or '',
            'first_name': tg_user.first_name or '',
            'last_name': tg_user.last_name or '',
        },
    )
    return user


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route message to appropriate handler"""
    user = await save_user(update.effective_user)
    text = update.message.text.strip()

    # Check if it's a URL
    downloader = DownloaderFactory.get_downloader(text)
    if downloader:
        await handle_download_request(update, context, user, text, downloader)
    else:
        # It's a search query
        await handle_search_request(update, context, user, text)
