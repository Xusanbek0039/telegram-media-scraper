import requests
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.models import SearchHistory, TelegramUser

ITUNES_SEARCH_URL = 'https://itunes.apple.com/search'


@sync_to_async
def save_user(telegram_user):
    user, _ = TelegramUser.objects.update_or_create(
        telegram_id=telegram_user.id,
        defaults={
            'username': telegram_user.username,
            'first_name': telegram_user.first_name or '',
            'last_name': telegram_user.last_name,
        },
    )
    return user


@sync_to_async
def save_search(user, query, results_count):
    SearchHistory.objects.create(
        user=user,
        query=query,
        results_count=results_count,
    )


def search_music(query):
    try:
        response = requests.get(
            ITUNES_SEARCH_URL,
            params={'term': query, 'media': 'music', 'limit': 5},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get('results', [])
    except requests.RequestException:
        return []


async def start_command(update: Update, context):
    user = await save_user(update.effective_user)
    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 🎵\n\n"
        "Men musiqa qidiruv botiman. Menga qo'shiq nomini yozing, "
        "men sizga iTunes'dan natijalarni topib beraman."
    )


async def search_handler(update: Update, context):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("Iltimos, qo'shiq nomini kiriting.")
        return

    user = await save_user(update.effective_user)
    await update.message.reply_text("🔍 Qidirilmoqda...")

    results = search_music(query)
    await save_search(user, query, len(results))

    if not results:
        await update.message.reply_text(
            "😔 Afsuski, hech qanday natija topilmadi. "
            "Boshqa so'rov bilan urinib ko'ring."
        )
        return

    text = f"🎵 \"{query}\" bo'yicha natijalar:\n\n"
    for i, track in enumerate(results, 1):
        track_name = track.get('trackName', 'Nomalum')
        artist = track.get('artistName', 'Nomalum')
        album = track.get('collectionName', 'Nomalum')
        preview_url = track.get('previewUrl', '')

        text += f"{i}. 🎶 {track_name}\n"
        text += f"   🎤 Ijrochi: {artist}\n"
        text += f"   💿 Albom: {album}\n"
        if preview_url:
            text += f"   🔗 Tinglash: {preview_url}\n"
        text += "\n"

    await update.message.reply_text(text)


class Command(BaseCommand):
    help = 'Telegram botni ishga tushirish'

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stderr.write(self.style.ERROR(
                'TELEGRAM_BOT_TOKEN .env faylida topilmadi!'
            ))
            return

        self.stdout.write(self.style.SUCCESS('Bot ishga tushmoqda...'))

        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler('start', start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

        self.stdout.write(self.style.SUCCESS('Bot muvaffaqiyatli ishga tushdi!'))
        app.run_polling()
