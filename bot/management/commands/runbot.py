import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from bot.models import TelegramUser, SearchHistory

ITUNES_SEARCH_URL = 'https://itunes.apple.com/search'


@sync_to_async
def save_user(tg_user):
    user, _ = TelegramUser.objects.update_or_create(
        telegram_id=tg_user.id,
        defaults={
            'username': tg_user.username or '',
            'first_name': tg_user.first_name or '',
            'last_name': tg_user.last_name or '',
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
    except Exception:
        return []


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update.effective_user)
    await update.message.reply_text(
        f"Salom, {update.effective_user.first_name}! 🎵\n\n"
        "Men sizga musiqa topishda yordam beraman.\n"
        "Qo'shiq nomini yoki artis ismini yozing, men sizga topib beraman!"
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await save_user(update.effective_user)
    query = update.message.text.strip()

    if not query:
        await update.message.reply_text("Iltimos, qo'shiq nomini yozing.")
        return

    await update.message.reply_text(f"🔍 \"{query}\" qidirilmoqda...")

    results = search_music(query)
    await save_search(user, query, len(results))

    if not results:
        await update.message.reply_text(
            f"\"{query}\" bo'yicha hech narsa topilmadi.\n"
            "Boshqa nom bilan qidirib ko'ring."
        )
        return

    for track in results:
        track_name = track.get('trackName', 'Noma\'lum')
        artist = track.get('artistName', 'Noma\'lum')
        album = track.get('collectionName', 'Noma\'lum')
        preview_url = track.get('previewUrl', '')
        track_url = track.get('trackViewUrl', '')

        text = (
            f"🎵 {track_name}\n"
            f"👤 Artis: {artist}\n"
            f"💿 Albom: {album}\n"
        )

        if track_url:
            text += f"🔗 [iTunes'da ochish]({track_url})\n"

        await update.message.reply_text(text, parse_mode='Markdown')

        if preview_url:
            try:
                await update.message.reply_audio(audio=preview_url)
            except Exception:
                pass


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

        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler('start', start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_command))

        self.stdout.write(self.style.SUCCESS('Bot tayyor! Ctrl+C bosib to\'xtatishingiz mumkin.'))
        app.run_polling(allowed_updates=Update.ALL_TYPES)
