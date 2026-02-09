"""Download handlers - routes to downloader services"""
import asyncio
import os
import shutil
from urllib.parse import quote

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.conf import settings

from core.models import DownloadHistory, TelegramUser
from services.downloaders.factory import DownloaderFactory

DOWNLOADS_DIR = os.path.join(settings.BASE_DIR, 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

PLATFORM_NAMES = {
    'youtube': 'YouTube',
    'instagram': 'Instagram',
    'tiktok': 'TikTok',
    'snapchat': 'Snapchat',
    'likee': 'Likee',
}


def format_filesize(size_bytes):
    """Format file size"""
    if not size_bytes:
        return '?MB'
    mb = size_bytes / (1024 * 1024)
    if mb >= 1:
        return f'{mb:.1f}MB'
    return f'{size_bytes / 1024:.0f}KB'


def build_youtube_keyboard(qualities, video_id):
    """Build YouTube quality selection keyboard"""
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
    """Build social media download keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📁 Video', callback_data=f'social_video_{platform}_{url_hash}'),
            InlineKeyboardButton('🎵 Audio', callback_data=f'social_audio_{platform}_{url_hash}'),
        ]
    ])


def _ffmpeg_available() -> bool:
    """
    ffmpeg bor-yo'qligini tekshiradi.
    yt-dlp audio extract/merge uchun va Shazam (pydub) uchun ffmpeg kerak bo'ladi.
    """
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return True
    # .env orqali berilgan holat (FFMPEG_PATH exe yoki papka bo'lishi mumkin)
    p = os.getenv("FFMPEG_PATH", "").strip()
    if not p:
        return False
    if os.path.isfile(p) and os.path.basename(p).lower().startswith("ffmpeg"):
        return True
    if os.path.isdir(p) and os.path.isfile(os.path.join(p, "ffmpeg.exe")):
        return True
    return False


def _build_instagram_keyboard(instagram_url: str, bot_username: str, url_hash: str) -> InlineKeyboardMarkup:
    """
    Instagram video tagidagi tugmalar:
    - Musiqasini qidirish (Shazam)
    - Do'stlarga yuborish (Share link)
    """
    bot_link = f"https://t.me/{bot_username}" if bot_username else ""
    share_text = f"Instagram videosi. Bot: {bot_link} | Dasturchi: @Husanbek_coder"
    share_url = f"https://t.me/share/url?url={quote(instagram_url)}&text={quote(share_text)}"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎧 Musiqasini qidirish", callback_data=f"music_instagram_{url_hash}")],
            [InlineKeyboardButton("📤 Do'stlarga yuborish", url=share_url)],
        ]
    )


async def _send_instagram_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, user, url: str, url_hash: str, downloader, info: dict):
    """
    Instagram link kelganda darhol video yuklab yuboradi.
    """
    platform = "instagram"
    platform_name = PLATFORM_NAMES.get(platform, platform)

    await update.message.reply_text("⏳ Instagram videosi yuklanmoqda...")

    # DownloadHistory yozuvi
    download_record = await sync_to_async(DownloadHistory.objects.create)(
        user=user,
        video_url=url,
        video_title=info.get("title", "Instagram Video"),
        platform=platform,
        format_label="Video",
        status="processing",
    )

    video_id = str(abs(hash(url)))[-10:]
    output_path = os.path.join(DOWNLOADS_DIR, f"{platform}_{video_id}.mp4")

    file_path = await asyncio.to_thread(downloader.download_video, url, output_path, None)
    if not file_path or not os.path.exists(file_path):
        download_record.status = "failed"
        download_record.error_message = "Download failed"
        await sync_to_async(download_record.save)()

        msg = (
            f"{platform_name} dan video yuklab bo'lmadi.\n\n"
            "Ko'p hollarda bu **ffmpeg** o'rnatilmaganligi sababli bo'ladi (video+audio merge uchun).\n"
            "Windows: `C:\\ffmpeg\\bin` ni PATH ga qo'shing yoki `.env` ga `FFMPEG_PATH=C:\\ffmpeg\\bin\\ffmpeg.exe` yozing."
        )
        await update.message.reply_text(msg)
        return

    try:
        download_record.status = "completed"
        download_record.file_size = os.path.getsize(file_path)
        from django.utils import timezone
        download_record.completed_at = await sync_to_async(timezone.now)()
        await sync_to_async(download_record.save)()

        me = await context.bot.get_me()
        bot_username = getattr(me, "username", "") or ""
        bot_link = f"https://t.me/{bot_username}" if bot_username else ""

        caption = (
            f"📁 {info.get('title', 'Instagram Video')}\n\n"
            f"🤖 Bot: {bot_link}\n"
            f"👨‍💻 Dasturchi: @Husanbek_coder"
        )
        keyboard = _build_instagram_keyboard(url, bot_username, url_hash)

        with open(file_path, "rb") as f:
            await update.message.reply_video(
                video=f,
                caption=caption,
                reply_markup=keyboard,
                supports_streaming=True,
            )
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass


async def handle_download_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user, url, downloader):
    """Handle download request - route to appropriate service"""
    platform = DownloaderFactory.detect_platform(url)
    platform_name = PLATFORM_NAMES.get(platform, platform)

    await update.message.reply_text("⏳ Ma'lumotlar olinmoqda...")

    # Get video info
    info = await asyncio.to_thread(downloader.get_info, url)
    if not info:
        await update.message.reply_text(f"{platform_name} dan ma'lumotlarni olishda xatolik yuz berdi.")
        return

    # Store in context for callback
    url_hash = str(abs(hash(url)))[-10:]
    context.user_data[f'url_{url_hash}'] = url
    context.user_data[f'platform_{url_hash}'] = platform

    if platform == 'youtube':
        # YouTube has quality options
        qualities = downloader.get_available_qualities(url)
        video_id = info.get('id', 'video')[:20]
        context.user_data[f'info_{url_hash}'] = info
        context.user_data[f'video_id_{url_hash}'] = video_id  # Store for callback lookup

        caption = f"📁 {info['title']}\n"
        if info.get('channel'):
            caption += f"👤 {info['channel']}\n"
        caption += "\nFormats to download ↓"

        keyboard = build_youtube_keyboard(qualities, video_id)

        if info.get('thumbnail'):
            try:
                await update.message.reply_photo(
                    photo=info['thumbnail'], caption=caption, reply_markup=keyboard,
                )
                return
            except Exception:
                pass
        await update.message.reply_text(caption, reply_markup=keyboard)
    else:
        # Instagram: link yuborilganda darhol video yuboramiz
        if platform == "instagram":
            context.user_data[f'info_{url_hash}'] = info
            await _send_instagram_direct(update, context, user, url, url_hash, downloader, info)
            return

        # Social media platforms
        keyboard = build_social_keyboard(platform, url_hash)
        context.user_data[f'info_{url_hash}'] = info

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


async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url_hash: str, format_type: str, quality: str = None):
    """Process download using appropriate service"""
    # Get message from update (callback query or regular message)
    if update.callback_query:
        query = update.callback_query
        message = query.message
    else:
        message = update.message
    
    if not message:
        print('[ERROR] Message topilmadi')
        return

    url = context.user_data.get(f'url_{url_hash}')
    platform = context.user_data.get(f'platform_{url_hash}')
    
    if not url:
        await message.reply_text("Havola topilmadi. Qayta yuboring.")
        return

    downloader = DownloaderFactory.get_downloader(url)
    if not downloader:
        await message.reply_text("Platforma aniqlanmadi.")
        return

    platform_name = PLATFORM_NAMES.get(platform, platform)
    info = context.user_data.get(f'info_{url_hash}', {})

    if format_type == 'video':
        await message.reply_text(f"⏳ {platform_name} dan video yuklanmoqda...")
        
        # Get user from update
        user_id = update.effective_user.id if update.effective_user else (update.callback_query.from_user.id if update.callback_query else None)
        if not user_id:
            await message.reply_text("Foydalanuvchi ma'lumotlari topilmadi.")
            return
        
        # Create download record
        user = await sync_to_async(TelegramUser.objects.get)(telegram_id=user_id)
        download_record = await sync_to_async(DownloadHistory.objects.create)(
            user=user,
            video_url=url,
            video_title=info.get('title', 'Video'),
            platform=platform,
            format_label='Video',
            status='processing',
        )

        video_id = str(abs(hash(url)))[-10:]
        output_path = os.path.join(DOWNLOADS_DIR, f'{platform}_{video_id}.mp4')
        
        file_path = await asyncio.to_thread(
            downloader.download_video, url, output_path, quality
        )

        if file_path and os.path.exists(file_path):
            try:
                file_size = os.path.getsize(file_path)
                download_record.status = 'completed'
                download_record.file_size = file_size
                from django.utils import timezone
                download_record.completed_at = await sync_to_async(timezone.now)()
                await sync_to_async(download_record.save)()

                with open(file_path, 'rb') as f:
                    await message.reply_video(
                        video=f,
                        caption=f"📁 {info.get('title', 'Video')}",
                        supports_streaming=True
                    )
            except Exception as e:
                download_record.status = 'failed'
                download_record.error_message = str(e)
                await sync_to_async(download_record.save)()
                await message.reply_text("Fayl juda katta yoki xatolik yuz berdi.")
            finally:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        else:
            download_record.status = 'failed'
            download_record.error_message = 'Download failed'
            await sync_to_async(download_record.save)()
            await message.reply_text("Video yuklab bo'lmadi.")

    elif format_type == 'audio':
        if not _ffmpeg_available():
            await message.reply_text(
                "🎵 Audio yuklash uchun **ffmpeg/ffprobe** kerak.\n\n"
                "Windows:\n"
                "- `C:\\ffmpeg\\bin` ni PATH ga qo'shing\n"
                "yoki `.env` ga:\n"
                "- `FFMPEG_PATH=C:\\ffmpeg\\bin\\ffmpeg.exe`\n\n"
                "So'ng botni qayta ishga tushiring."
            )
            return

        await message.reply_text(f"⏳ {platform_name} dan audio yuklanmoqda...")
        
        # Get user from update
        user_id = update.effective_user.id if update.effective_user else (update.callback_query.from_user.id if update.callback_query else None)
        if not user_id:
            await message.reply_text("Foydalanuvchi ma'lumotlari topilmadi.")
            return
        
        user = await sync_to_async(TelegramUser.objects.get)(telegram_id=user_id)
        download_record = await sync_to_async(DownloadHistory.objects.create)(
            user=user,
            video_url=url,
            video_title=info.get('title', 'Audio'),
            platform=platform,
            format_label='Audio',
            status='processing',
        )

        video_id = str(abs(hash(url)))[-10:]
        output_path = os.path.join(DOWNLOADS_DIR, f'{platform}_{video_id}_audio.mp3')
        
        file_path = await asyncio.to_thread(downloader.download_audio, url, output_path)

        if file_path and os.path.exists(file_path):
            try:
                file_size = os.path.getsize(file_path)
                download_record.status = 'completed'
                download_record.file_size = file_size
                from django.utils import timezone
                download_record.completed_at = await sync_to_async(timezone.now)()
                await sync_to_async(download_record.save)()

                with open(file_path, 'rb') as f:
                    await message.reply_audio(
                        audio=f,
                        title=info.get('title', 'Audio'),
                        caption=f"🎵 {info.get('title', 'Audio')}"
                    )
            except Exception as e:
                download_record.status = 'failed'
                download_record.error_message = str(e)
                await sync_to_async(download_record.save)()
                await message.reply_text("Xatolik yuz berdi.")
            finally:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        else:
            download_record.status = 'failed'
            download_record.error_message = 'Download failed'
            await sync_to_async(download_record.save)()
            await message.reply_text("Audio yuklab bo'lmadi.")
