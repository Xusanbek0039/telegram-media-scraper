"""Callback handlers"""
import asyncio
import os
from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.conf import settings

from core.models import TelegramUser, DownloadHistory
from django.utils import timezone
from services.downloaders.factory import DownloaderFactory
from .download import process_download
from .search import format_results, build_search_keyboard

DOWNLOADS_DIR = os.path.join(settings.BASE_DIR, 'downloads')


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
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
        
        # Download audio
        url = track['url']
        downloader = DownloaderFactory.get_downloader(url)
        if not downloader:
            await query.message.reply_text("Yuklab bo'lmadi.")
            return

        video_id = track['id']
        output_path = os.path.join(DOWNLOADS_DIR, f'{video_id}_audio.mp3')
        
        file_path = await asyncio.to_thread(downloader.download_audio, url, output_path)
        
        if file_path and os.path.exists(file_path):
            try:
                user = await sync_to_async(TelegramUser.objects.get)(telegram_id=query.from_user.id)
                await sync_to_async(DownloadHistory.objects.create)(
                    user=user,
                    video_url=url,
                    video_title=track['title'],
                    platform='youtube',
                    format_label='Audio',
                    status='completed',
                    file_size=os.path.getsize(file_path),
                    completed_at=await sync_to_async(timezone.now)(),
                )
                with open(file_path, 'rb') as f:
                    await query.message.reply_audio(
                        audio=f, title=track['title'], caption=f"🎵 {track['title']}"
                    )
            except Exception:
                await query.message.reply_text("Xatolik yuz berdi.")
            finally:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        else:
            await query.message.reply_text("Audio yuklab bo'lmadi.")
        return

    if data.startswith('ytdl_'):
        parts = data.split('_', 2)
        callback_video_id = parts[1]
        quality = parts[2]
        
        # Get info and URL from context using video_id
        info = None
        url = None
        url_hash = None
        
        # Try to find matching context data by video_id
        for key in list(context.user_data.keys()):
            if key.startswith('video_id_'):
                stored_hash = key.replace('video_id_', '')
                stored_video_id = context.user_data.get(key)
                if stored_video_id == callback_video_id:
                    url_hash = stored_hash
                    url = context.user_data.get(f'url_{stored_hash}')
                    info = context.user_data.get(f'info_{stored_hash}')
                    break
        
        # Fallback: try to match by info
        if not info or not url:
            for key in list(context.user_data.keys()):
                if key.startswith('info_'):
                    stored_hash = key.replace('info_', '')
                    stored_info = context.user_data.get(key)
                    stored_url = context.user_data.get(f'url_{stored_hash}')
                    if stored_info and stored_url:
                        stored_video_id = str(stored_info.get('id', ''))[:20]
                        if stored_video_id == callback_video_id:
                            info = stored_info
                            url = stored_url
                            url_hash = stored_hash
                            break
        
        if not info or not url:
            await query.message.reply_text("Video ma'lumotlari topilmadi. Havolani qayta yuboring.")
            return

        label = f'{quality}p' if quality != 'audio' else 'Audio'
        await query.message.reply_text(f"⏳ \"{info['title']}\" ({label}) yuklanmoqda...")

        downloader = DownloaderFactory.get_downloader(url)
        if not downloader:
            await query.message.reply_text("Yuklab bo'lmadi.")
            return

        video_id_hash = str(abs(hash(url)))[-10:]
        output_path = os.path.join(DOWNLOADS_DIR, f'youtube_{video_id_hash}_{quality}.mp4' if quality != 'audio' else f'youtube_{video_id_hash}_audio.mp3')

        if quality == 'audio':
            file_path = await asyncio.to_thread(downloader.download_audio, url, output_path)
        else:
            file_path = await asyncio.to_thread(downloader.download_video, url, output_path, quality)

        if file_path and os.path.exists(file_path):
            try:
                user = await sync_to_async(TelegramUser.objects.get)(telegram_id=query.from_user.id)
                await sync_to_async(DownloadHistory.objects.create)(
                    user=user,
                    video_url=url,
                    video_title=info['title'],
                    platform='youtube',
                    format_label=label,
                    status='completed',
                    file_size=os.path.getsize(file_path),
                    completed_at=await sync_to_async(timezone.now)(),
                )
                with open(file_path, 'rb') as f:
                    if quality == 'audio':
                        await query.message.reply_audio(
                            audio=f, title=info['title'], caption=f"🎵 {info['title']}"
                        )
                    else:
                        await query.message.reply_video(
                            video=f, caption=f"📁 {info['title']} ({label})", supports_streaming=True
                        )
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
        if len(parts) < 4:
            await query.message.reply_text("Xatolik: noto'g'ri callback data.")
            return
        
        action = parts[1]  # 'video' or 'audio'
        platform = parts[2]
        url_hash = parts[3]

        try:
            await process_download(update, context, url_hash, action, None)
        except Exception as e:
            print(f'[ERROR] process_download xatolik: {e}')
            await query.message.reply_text("Yuklashda xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return
