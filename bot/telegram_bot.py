import asyncio
import os
import re
import threading
import tempfile
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

URL_PATTERNS = {
    'youtube': re.compile(
        r'(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w\-]+'
    ),
    'instagram': re.compile(
        r'(https?://)?(www\.)?(instagram\.com/(p|reel|tv|reels)/[\w\-]+)'
    ),
    'tiktok': re.compile(
        r'(https?://)?(www\.|vm\.|vt\.)?tiktok\.com/[\w\-@/.]+'
    ),
    'snapchat': re.compile(
        r'(https?://)?(www\.)?(snapchat\.com|story\.snapchat\.com)/[\w\-/.]+'
    ),
    'likee': re.compile(
        r'(https?://)?(www\.|l\.)?(likee\.video|like\.video)/[\w\-/.]+'
    ),
}

PLATFORM_NAMES = {
    'youtube': 'YouTube',
    'instagram': 'Instagram',
    'tiktok': 'TikTok',
    'snapchat': 'Snapchat',
    'likee': 'Likee',
}

VIDEO_QUALITIES = ['144', '240', '360', '480', '720', '1080']


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
        user=user, video_url=video_url, video_title=video_title, format_label=format_label,
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
    return f'{size_bytes / 1024:.0f}KB'


def detect_platform(text):
    for platform, pattern in URL_PATTERNS.items():
        match = pattern.search(text)
        if match:
            return platform, match.group(0)
    return None, None


def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Video'),
                'channel': info.get('channel', info.get('uploader', '')),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'formats': info.get('formats', []),
                'url': url,
                'id': info.get('id', 'video'),
            }
        except Exception:
            return None


def get_available_qualities(formats):
    available = []
    seen = set()
    for f in formats:
        height = f.get('height')
        if not height or f.get('vcodec') == 'none':
            continue
        label = str(height)
        if label not in seen and label in VIDEO_QUALITIES:
            filesize = f.get('filesize') or f.get('filesize_approx') or 0
            seen.add(label)
            available.append({'label': f'{label}p', 'height': label, 'filesize': filesize})

    available.sort(key=lambda x: int(x['height']))

    audio_size = 0
    for f in formats:
        if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
            audio_size = f.get('filesize') or f.get('filesize_approx') or 0
            break
    available.append({'label': 'Audio', 'height': 'audio', 'filesize': audio_size})

    return available


def download_media(url, quality, video_id):
    if quality == 'audio':
        output_path = os.path.join(DOWNLOADS_DIR, f'{video_id}_audio.mp3')
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
            'noplaylist': True,
        }
    else:
        output_path = os.path.join(DOWNLOADS_DIR, f'{video_id}_{quality}.mp4')
        ydl_opts = {
            'format': f'best[height<={quality}][ext=mp4]/best[height<={quality}]/best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, f'{video_id}_{quality}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'merge_output_format': 'mp4',
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if os.path.exists(output_path):
        return output_path

    for ext in ['mp4', 'webm', 'mkv', 'mp3', 'm4a']:
        alt = os.path.join(DOWNLOADS_DIR, f'{video_id}_{quality}.{ext}')
        if os.path.exists(alt):
            return alt
    return None


def download_social_video(url, platform):
    video_id = str(hash(url))[-10:]
    output_path = os.path.join(DOWNLOADS_DIR, f'{platform}_{video_id}.mp4')

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(DOWNLOADS_DIR, f'{platform}_{video_id}.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get('title', 'Video')

    if os.path.exists(output_path):
        return output_path, title

    for ext in ['mp4', 'webm', 'mkv']:
        alt = os.path.join(DOWNLOADS_DIR, f'{platform}_{video_id}.{ext}')
        if os.path.exists(alt):
            return alt, title
    return None, title


def download_social_audio(url, platform):
    video_id = str(hash(url))[-10:]
    output_path = os.path.join(DOWNLOADS_DIR, f'{platform}_{video_id}_audio.mp3')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOADS_DIR, f'{platform}_{video_id}_audio.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get('title', 'Audio')

    if os.path.exists(output_path):
        return output_path, title
    return None, title


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
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    })
            return results
        except Exception:
            return []


async def recognize_shazam(file_path):
    from shazamio import Shazam
    shazam = Shazam()
    try:
        result = await shazam.recognize(file_path)
        track = result.get('track')
        if not track:
            return None
        return {
            'title': track.get('title', 'Noma\'lum'),
            'artist': track.get('subtitle', 'Noma\'lum'),
            'album': track.get('sections', [{}])[0].get('metadata', [{}])[0].get('text', '') if track.get('sections') else '',
            'genre': track.get('genres', {}).get('primary', ''),
            'shazam_url': track.get('url', ''),
            'cover': track.get('images', {}).get('coverarthq', ''),
            'lyrics': '',
        }
    except Exception:
        return None


def build_youtube_keyboard(qualities, video_id):
    rows = []
    row = []
    for fmt in qualities:
        label = fmt['label']
        size = format_filesize(fmt['filesize'])
        icon = '🎵' if label == 'Audio' else '📁'
        btn_text = f"{icon} {label} - {size}"
        callback = f"ytdl_{video_id}_{fmt['height']}"
        row.append(InlineKeyboardButton(btn_text, callback_data=callback))
        if len(row) == 2 or label == 'Audio':
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def build_social_keyboard(platform, url_hash):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📁 Video', callback_data=f'social_video_{platform}_{url_hash}'),
            InlineKeyboardButton('🎵 Audio', callback_data=f'social_audio_{platform}_{url_hash}'),
        ]
    ])


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


def format_results(results, page=0):
    start = page * 10
    page_results = results[start:start + 10]
    lines = []
    for i, track in enumerate(page_results):
        num = start + i + 1
        lines.append(f'{num}. {track["title"]} {format_duration(track.get("duration"))}')
    return '\n'.join(lines)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update.effective_user)
    await update.message.reply_text(
        f"Salom, {update.effective_user.first_name}! 🎵\n\n"
        "🔍 Qo'shiq nomini yozing — men topib beraman\n\n"
        "📥 Quyidagi platformalar havolasini yuboring:\n"
        "• YouTube (video + shorts)\n"
        "• Instagram (post, reel, IGTV)\n"
        "• TikTok (suv belgisiz)\n"
        "• Snapchat\n"
        "• Likee\n\n"
        "🎤 Shazam:\n"
        "• Ovozli xabar yuboring\n"
        "• Audio/video yuboring\n"
        "• Video xabar yuboring\n"
        "— qo'shiqni aniqlab beraman!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await save_user(update.effective_user)
    text = update.message.text.strip()

    platform, url = detect_platform(text)

    if platform == 'youtube':
        await handle_youtube_url(update, context, user, url)
    elif platform in ('instagram', 'tiktok', 'snapchat', 'likee'):
        await handle_social_url(update, context, user, platform, url)
    else:
        await handle_search(update, context, user, text)


async def handle_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE, user, url):
    await update.message.reply_text("⏳ Video ma'lumotlari olinmoqda...")

    info = await asyncio.to_thread(get_video_info, url)
    if not info:
        await update.message.reply_text("Video ma'lumotlarini olishda xatolik yuz berdi.")
        return

    context.user_data['video_info'] = info
    qualities = get_available_qualities(info['formats'])

    caption = f"📁 {info['title']}\n"
    if info.get('channel'):
        caption += f"👤 {info['channel']}\n"
    caption += "\nFormats to download ↓"

    keyboard = build_youtube_keyboard(qualities, info['id'][:20])

    if info.get('thumbnail'):
        try:
            await update.message.reply_photo(
                photo=info['thumbnail'], caption=caption, reply_markup=keyboard,
            )
            return
        except Exception:
            pass
    await update.message.reply_text(caption, reply_markup=keyboard)


async def handle_social_url(update: Update, context: ContextTypes.DEFAULT_TYPE, user, platform, url):
    platform_name = PLATFORM_NAMES.get(platform, platform)
    url_hash = str(abs(hash(url)))[-10:]
    context.user_data[f'social_url_{url_hash}'] = url

    await update.message.reply_text("⏳ Ma'lumotlar olinmoqda...")

    info = await asyncio.to_thread(get_video_info, url)
    if not info:
        await update.message.reply_text(f"{platform_name} dan yuklab bo'lmadi. Havolani tekshiring.")
        return

    context.user_data[f'social_info_{url_hash}'] = info
    keyboard = build_social_keyboard(platform, url_hash)

    caption = f"📁 {info['title']}\n"
    if info.get('channel'):
        caption += f"👤 {info['channel']}\n"
    caption += f"\n📥 {platform_name} dan yuklash ↓"

    if info.get('thumbnail'):
        try:
            await update.message.reply_photo(
                photo=info['thumbnail'], caption=caption, reply_markup=keyboard,
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
            f"\"{query}\" bo'yicha hech narsa topilmadi.\nBoshqa nom bilan qidirib ko'ring."
        )
        return

    context.user_data['results'] = results
    context.user_data['page'] = 0
    text = format_results(results, page=0)
    await update.message.reply_text(text, reply_markup=build_search_keyboard(page=0))


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update.effective_user)
    await update.message.reply_text("🎤 Qo'shiq aniqlanmoqda...")

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    file = await context.bot.get_file(voice.file_id)
    tmp = os.path.join(DOWNLOADS_DIR, f'shazam_{update.message.message_id}.ogg')
    await file.download_to_drive(tmp)

    try:
        result = await recognize_shazam(tmp)
        if result:
            await send_shazam_result(update, result)
        else:
            await update.message.reply_text("Qo'shiqni aniqlab bo'lmadi. Qaytadan urinib ko'ring.")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update.effective_user)
    await update.message.reply_text("🎤 Qo'shiq aniqlanmoqda...")

    video = update.message.video or update.message.video_note
    if not video:
        return

    file = await context.bot.get_file(video.file_id)
    tmp = os.path.join(DOWNLOADS_DIR, f'shazam_video_{update.message.message_id}.mp4')
    await file.download_to_drive(tmp)

    try:
        result = await recognize_shazam(tmp)
        if result:
            await send_shazam_result(update, result)
        else:
            await update.message.reply_text("Qo'shiqni aniqlab bo'lmadi. Qaytadan urinib ko'ring.")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


async def handle_audio_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update.effective_user)
    await update.message.reply_text("🎤 Qo'shiq aniqlanmoqda...")

    audio = update.message.audio or update.message.document
    if not audio:
        return

    file = await context.bot.get_file(audio.file_id)
    ext = 'mp3'
    if hasattr(audio, 'file_name') and audio.file_name:
        ext = audio.file_name.split('.')[-1] if '.' in audio.file_name else 'mp3'
    tmp = os.path.join(DOWNLOADS_DIR, f'shazam_audio_{update.message.message_id}.{ext}')
    await file.download_to_drive(tmp)

    try:
        result = await recognize_shazam(tmp)
        if result:
            await send_shazam_result(update, result)
        else:
            await update.message.reply_text("Qo'shiqni aniqlab bo'lmadi. Qaytadan urinib ko'ring.")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


async def send_shazam_result(update, result):
    text = (
        f"🎵 <b>{result['title']}</b>\n"
        f"👤 <b>Ijrochi:</b> {result['artist']}\n"
    )
    if result.get('album'):
        text += f"💿 <b>Albom:</b> {result['album']}\n"
    if result.get('genre'):
        text += f"🎶 <b>Janr:</b> {result['genre']}\n"
    if result.get('shazam_url'):
        text += f"\n🔗 <a href=\"{result['shazam_url']}\">Shazam da ochish</a>"

    if result.get('cover'):
        try:
            await update.message.reply_photo(photo=result['cover'], caption=text, parse_mode='HTML')
            return
        except Exception:
            pass
    await update.message.reply_text(text, parse_mode='HTML')


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
        await query.message.edit_text(text, reply_markup=build_search_keyboard(page=page))
        return

    if data.startswith('select_'):
        results = context.user_data.get('results', [])
        index = int(data.split('_')[1])
        if index < 0 or index >= len(results):
            return
        track = results[index]
        await query.message.reply_text(f"⏳ \"{track['title']}\" yuklanmoqda...")
        audio_path = await asyncio.to_thread(download_media, track['url'], 'audio', track['id'])
        if audio_path and os.path.exists(audio_path):
            try:
                user = await save_user(query.from_user)
                await save_download(user, track['url'], track['title'], 'Audio')
                with open(audio_path, 'rb') as f:
                    await query.message.reply_audio(audio=f, title=track['title'], caption=f"🎵 {track['title']}")
            except Exception:
                await query.message.reply_text("Xatolik yuz berdi.")
            finally:
                try:
                    os.remove(audio_path)
                except OSError:
                    pass
        else:
            await query.message.reply_text("Audio yuklab bo'lmadi.")
        return

    if data.startswith('ytdl_'):
        parts = data.split('_', 2)
        video_id = parts[1]
        quality = parts[2]
        info = context.user_data.get('video_info')
        if not info:
            await query.message.reply_text("Video ma'lumotlari topilmadi. Havolani qayta yuboring.")
            return

        label = f'{quality}p' if quality != 'audio' else 'Audio'
        await query.message.reply_text(f"⏳ \"{info['title']}\" ({label}) yuklanmoqda...")

        file_path = await asyncio.to_thread(download_media, info['url'], quality, video_id)
        if file_path and os.path.exists(file_path):
            try:
                user = await save_user(query.from_user)
                await save_download(user, info['url'], info['title'], label)
                with open(file_path, 'rb') as f:
                    if quality == 'audio':
                        await query.message.reply_audio(audio=f, title=info['title'], caption=f"🎵 {info['title']}")
                    else:
                        await query.message.reply_video(video=f, caption=f"📁 {info['title']} ({label})", supports_streaming=True)
            except Exception:
                await query.message.reply_text("Fayl juda katta yoki xatolik yuz berdi. Kichikroq formatni tanlang.")
            finally:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        else:
            await query.message.reply_text("Yuklab bo'lmadi. Boshqa formatni tanlang.")
        return

    if data.startswith('social_video_') or data.startswith('social_audio_'):
        parts = data.split('_')
        action = parts[1]
        platform = parts[2]
        url_hash = parts[3]

        url = context.user_data.get(f'social_url_{url_hash}')
        if not url:
            await query.message.reply_text("Havola topilmadi. Qayta yuboring.")
            return

        platform_name = PLATFORM_NAMES.get(platform, platform)
        await query.message.reply_text(f"⏳ {platform_name} dan yuklanmoqda...")

        if action == 'video':
            file_path, title = await asyncio.to_thread(download_social_video, url, platform)
            if file_path and os.path.exists(file_path):
                try:
                    user = await save_user(query.from_user)
                    await save_download(user, url, title, f'{platform_name} Video')
                    with open(file_path, 'rb') as f:
                        await query.message.reply_video(video=f, caption=f"📁 {title}", supports_streaming=True)
                except Exception:
                    await query.message.reply_text("Fayl juda katta yoki xatolik yuz berdi.")
                finally:
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
            else:
                await query.message.reply_text("Video yuklab bo'lmadi.")
        else:
            file_path, title = await asyncio.to_thread(download_social_audio, url, platform)
            if file_path and os.path.exists(file_path):
                try:
                    user = await save_user(query.from_user)
                    await save_download(user, url, title, f'{platform_name} Audio')
                    with open(file_path, 'rb') as f:
                        await query.message.reply_audio(audio=f, title=title, caption=f"🎵 {title}")
                except Exception:
                    await query.message.reply_text("Xatolik yuz berdi.")
                finally:
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
            else:
                await query.message.reply_text("Audio yuklab bo'lmadi.")


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
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, handle_video))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print('[BOT] Telegram bot ishga tushdi!')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def start_bot():
    bot_thread = threading.Thread(target=_run_bot, daemon=True)
    bot_thread.start()
