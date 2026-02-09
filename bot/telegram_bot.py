import asyncio
import os
import threading
import yt_dlp
from django.conf import settings
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes,
)

from bot.models import TelegramUser, SearchHistory

RESULTS_DIR = os.path.join(settings.BASE_DIR, 'downloads')
os.makedirs(RESULTS_DIR, exist_ok=True)


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
    SearchHistory.objects.create(user=user, query=query, results_count=results_count)


def format_duration(seconds):
    if not seconds:
        return '0:00'
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f'{minutes}:{secs:02d}'


def search_youtube(query, limit=10):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': f'ytsearch{limit}',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(query, download=False)
            entries = result.get('entries', [])
            results = []
            for entry in entries:
                if entry:
                    results.append({
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Noma\'lum'),
                        'duration': entry.get('duration', 0),
                        'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    })
            return results
        except Exception:
            return []


def download_audio(video_id):
    output_path = os.path.join(RESULTS_DIR, f'{video_id}.mp3')
    if os.path.exists(output_path):
        return output_path

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(RESULTS_DIR, f'{video_id}.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }
    url = f'https://www.youtube.com/watch?v={video_id}'
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if os.path.exists(output_path):
        return output_path
    return None


def build_keyboard(page=0):
    start = page * 10
    row1 = [InlineKeyboardButton(str(start + i + 1), callback_data=f'select_{start + i}') for i in range(5)]
    row2 = [InlineKeyboardButton(str(start + i + 6), callback_data=f'select_{start + i + 5}') for i in range(5)]
    row3 = [
        InlineKeyboardButton('⬅️', callback_data=f'page_{page - 1}'),
        InlineKeyboardButton('❌', callback_data='cancel'),
        InlineKeyboardButton('➡️', callback_data=f'page_{page + 1}'),
    ]
    return InlineKeyboardMarkup([row1, row2, row3])


def format_results(results, page=0):
    start = page * 10
    page_results = results[start:start + 10]
    lines = []
    for i, track in enumerate(page_results):
        num = start + i + 1
        title = track['title']
        duration = format_duration(track.get('duration'))
        lines.append(f'{num}. {title} {duration}')
    return '\n'.join(lines)


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

    results = await asyncio.to_thread(search_youtube, query)
    await save_search(user, query, len(results))

    if not results:
        await update.message.reply_text(
            f"\"{query}\" bo'yicha hech narsa topilmadi.\n"
            "Boshqa nom bilan qidirib ko'ring."
        )
        return

    context.user_data['results'] = results
    context.user_data['page'] = 0

    text = format_results(results, page=0)
    keyboard = build_keyboard(page=0)
    await update.message.reply_text(text, reply_markup=keyboard)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    results = context.user_data.get('results', [])

    if data == 'cancel':
        await query.message.delete()
        context.user_data.pop('results', None)
        context.user_data.pop('page', None)
        return

    if data.startswith('page_'):
        page = int(data.split('_')[1])
        if page < 0 or page * 10 >= len(results):
            return
        context.user_data['page'] = page
        text = format_results(results, page=page)
        keyboard = build_keyboard(page=page)
        await query.message.edit_text(text, reply_markup=keyboard)
        return

    if data.startswith('select_'):
        index = int(data.split('_')[1])
        if index < 0 or index >= len(results):
            return

        track = results[index]
        await query.message.reply_text(f"⏳ \"{track['title']}\" yuklanmoqda...")

        audio_path = await asyncio.to_thread(download_audio, track['id'])

        if audio_path and os.path.exists(audio_path):
            try:
                with open(audio_path, 'rb') as audio_file:
                    await query.message.reply_audio(
                        audio=audio_file,
                        title=track['title'],
                        caption=f"🎵 {track['title']}",
                    )
            except Exception:
                await query.message.reply_text("Xatolik yuz berdi. Qaytadan urinib ko'ring.")
            finally:
                try:
                    os.remove(audio_path)
                except OSError:
                    pass
        else:
            await query.message.reply_text("Audio yuklab bo'lmadi. Boshqa qo'shiqni tanlang.")


def _run_bot():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        print('[BOT] TELEGRAM_BOT_TOKEN .env faylida topilmadi!')
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_command))

    print('[BOT] Telegram bot ishga tushdi!')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def start_bot():
    bot_thread = threading.Thread(target=_run_bot, daemon=True)
    bot_thread.start()
