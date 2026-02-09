import asyncio
import os
import re
import threading
import yt_dlp
from django.conf import settings
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes,
)

from bot.models import TelegramUser, SearchHistory, DownloadHistory

DOWNLOADS_DIR = os.path.join(settings.BASE_DIR, 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+'
)

VIDEO_FORMATS = [
    ('144p', '160'),
    ('240p', '133'),
    ('360p', '18'),
    ('480p', '135'),
    ('720p', '22'),
    ('1080p', '137'),
]


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


@sync_to_async
def save_download(user, video_url, video_title, format_label):
    DownloadHistory.objects.create(
        user=user,
        video_url=video_url,
        video_title=video_title,
        format_label=format_label,
    )


def format_duration(seconds):
    if not seconds:
        return '0:00'
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f'{minutes}:{secs:02d}'


def format_filesize(size_bytes):
    if not size_bytes:
        return '?MB'
    mb = size_bytes / (1024 * 1024)
    if mb >= 1:
        return f'{mb:.1f}MB'
    kb = size_bytes / 1024
    return f'{kb:.0f}KB'


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


def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Noma\'lum')
            channel = info.get('channel', info.get('uploader', 'Noma\'lum'))
            thumbnail = info.get('thumbnail', '')

            available_formats = []
            formats = info.get('formats', [])

            for label, fmt_id in VIDEO_FORMATS:
                for f in formats:
                    if f.get('format_id') == fmt_id:
                        filesize = f.get('filesize') or f.get('filesize_approx') or 0
                        available_formats.append({
                            'label': label,
                            'format_id': fmt_id,
                            'filesize': filesize,
                        })
                        break

            if not available_formats:
                for f in formats:
                    height = f.get('height')
                    if height and f.get('vcodec') != 'none':
                        label = f'{height}p'
                        filesize = f.get('filesize') or f.get('filesize_approx') or 0
                        if not any(af['label'] == label for af in available_formats):
                            available_formats.append({
                                'label': label,
                                'format_id': f.get('format_id', ''),
                                'filesize': filesize,
                            })

            audio_size = 0
            for f in formats:
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    audio_size = f.get('filesize') or f.get('filesize_approx') or 0
                    break

            available_formats.append({
                'label': 'Audio',
                'format_id': 'audio',
                'filesize': audio_size,
            })

            return {
                'title': title,
                'channel': channel,
                'thumbnail': thumbnail,
                'formats': available_formats,
                'url': url,
            }
        except Exception:
            return None


def download_video(url, format_id, video_id):
    if format_id == 'audio':
        ext = 'mp3'
        output_path = os.path.join(DOWNLOADS_DIR, f'{video_id}_audio.{ext}')
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, f'{video_id}_audio.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
    else:
        ext = 'mp4'
        output_path = os.path.join(DOWNLOADS_DIR, f'{video_id}_{format_id}.{ext}')
        ydl_opts = {
            'format': f'{format_id}+bestaudio/best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, f'{video_id}_{format_id}.%(ext)s'),
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if os.path.exists(output_path):
        return output_path
    return None


def build_search_keyboard(page=0):
    start = page * 10
    row1 = [InlineKeyboardButton(str(start + i + 1), callback_data=f'select_{start + i}') for i in range(5)]
    row2 = [InlineKeyboardButton(str(start + i + 6), callback_data=f'select_{start + i + 5}') for i in range(5)]
    row3 = [
        InlineKeyboardButton('⬅️', callback_data=f'page_{page - 1}'),
        InlineKeyboardButton('❌', callback_data='cancel'),
        InlineKeyboardButton('➡️', callback_data=f'page_{page + 1}'),
    ]
    return InlineKeyboardMarkup([row1, row2, row3])


def build_format_keyboard(formats, video_id):
    rows = []
    row = []
    for i, fmt in enumerate(formats):
        label = fmt['label']
        size = format_filesize(fmt['filesize'])
        icon = '🎵' if label == 'Audio' else '📁'
        btn_text = f"{icon} {label} - {size}"
        callback = f"dl_{video_id}_{fmt['format_id']}"
        row.append(InlineKeyboardButton(btn_text, callback_data=callback))
        if len(row) == 2 or label == 'Audio':
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


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
        "Qo'shiq nomini yoki artis ismini yozing, men sizga topib beraman!\n\n"
        "YouTube havolasini yuborsangiz, videoni yuklab beraman!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await save_user(update.effective_user)
    text = update.message.text.strip()

    if YOUTUBE_REGEX.search(text):
        await handle_youtube_url(update, context, user, text)
    else:
        await handle_search(update, context, user, text)


async def handle_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE, user, url):
    await update.message.reply_text("⏳ Video ma'lumotlari olinmoqda...")

    info = await asyncio.to_thread(get_video_info, url)

    if not info:
        await update.message.reply_text("Video ma'lumotlarini olishda xatolik yuz berdi.")
        return

    context.user_data['video_info'] = info

    caption = (
        f"📁 {info['title']}\n\n"
        f"👤 {info['channel']} →\n\n"
        f"Formats to download ↓"
    )

    keyboard = build_format_keyboard(info['formats'], info.get('id', 'vid'))

    if info.get('thumbnail'):
        try:
            await update.message.reply_photo(
                photo=info['thumbnail'],
                caption=caption,
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass

    await update.message.reply_text(caption, reply_markup=keyboard)


async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE, user, query):
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
    keyboard = build_search_keyboard(page=0)
    await update.message.reply_text(text, reply_markup=keyboard)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'cancel':
        await query.message.delete()
        context.user_data.pop('results', None)
        context.user_data.pop('page', None)
        return

    if data.startswith('page_'):
        results = context.user_data.get('results', [])
        page = int(data.split('_')[1])
        if page < 0 or page * 10 >= len(results):
            return
        context.user_data['page'] = page
        text = format_results(results, page=page)
        keyboard = build_search_keyboard(page=page)
        await query.message.edit_text(text, reply_markup=keyboard)
        return

    if data.startswith('select_'):
        results = context.user_data.get('results', [])
        index = int(data.split('_')[1])
        if index < 0 or index >= len(results):
            return
        track = results[index]
        await query.message.reply_text(f"⏳ \"{track['title']}\" yuklanmoqda...")
        audio_path = await asyncio.to_thread(download_video, track['url'], 'audio', track['id'])
        if audio_path and os.path.exists(audio_path):
            try:
                user = await save_user(query.from_user)
                await save_download(user, track['url'], track['title'], 'Audio')
                with open(audio_path, 'rb') as f:
                    await query.message.reply_audio(
                        audio=f, title=track['title'], caption=f"🎵 {track['title']}"
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
        return

    if data.startswith('dl_'):
        parts = data.split('_', 2)
        if len(parts) < 3:
            return
        format_id = parts[2]

        video_info = context.user_data.get('video_info')
        if not video_info:
            await query.message.reply_text("Video ma'lumotlari topilmadi. Havolani qayta yuboring.")
            return

        fmt_label = format_id
        for fmt in video_info.get('formats', []):
            if fmt['format_id'] == format_id:
                fmt_label = fmt['label']
                break

        url = video_info['url']
        title = video_info['title']
        video_id = url.split('=')[-1].split('/')[-1][:20]

        await query.message.reply_text(f"⏳ \"{title}\" ({fmt_label}) yuklanmoqda...")

        file_path = await asyncio.to_thread(download_video, url, format_id, video_id)

        if file_path and os.path.exists(file_path):
            try:
                user = await save_user(query.from_user)
                await save_download(user, url, title, fmt_label)
                with open(file_path, 'rb') as f:
                    if format_id == 'audio':
                        await query.message.reply_audio(
                            audio=f, title=title, caption=f"🎵 {title}"
                        )
                    else:
                        await query.message.reply_video(
                            video=f, caption=f"📁 {title} ({fmt_label})",
                            supports_streaming=True,
                        )
            except Exception:
                await query.message.reply_text(
                    "Fayl juda katta yoki xatolik yuz berdi. Kichikroq formatni tanlang."
                )
            finally:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        else:
            await query.message.reply_text("Yuklab bo'lmadi. Boshqa formatni tanlang.")


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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print('[BOT] Telegram bot ishga tushdi!')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def start_bot():
    bot_thread = threading.Thread(target=_run_bot, daemon=True)
    bot_thread.start()
