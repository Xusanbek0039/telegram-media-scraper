"""Callback handlers"""
import asyncio
import os
from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.conf import settings

from core.models import TelegramUser, DownloadHistory
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
                user = await sync_to_async(lambda: TelegramUser.objects.get(telegram_id=query.from_user.id))()
                await sync_to_async(DownloadHistory.objects.create)(
                    user=user,
                    video_url=url,
                    video_title=track['title'],
                    platform='youtube',
                    format_label='Audio',
                    status='completed',
                    file_size=os.path.getsize(file_path),
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
        video_id = parts[1]
        quality = parts[2]
        info = context.user_data.get('video_info')
        
        # Try to get from url_hash context
        for key in context.user_data:
            if key.startswith('info_'):
                info = context.user_data[key]
                url_hash = key.replace('info_', '')
                break
        
        if not info:
            await query.message.reply_text("Video ma'lumotlari topilmadi. Havolani qayta yuboring.")
            return

        label = f'{quality}p' if quality != 'audio' else 'Audio'
        await query.message.reply_text(f"⏳ \"{info['title']}\" ({label}) yuklanmoqda...")

        # Get URL from context
        url = None
        for key in context.user_data:
            if key.startswith('url_'):
                url = context.user_data[key]
                url_hash = key.replace('url_', '')
                break

        if not url:
            await query.message.reply_text("Havola topilmadi.")
            return

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
                user = await sync_to_async(lambda: TelegramUser.objects.get(telegram_id=query.from_user.id))()
                await sync_to_async(DownloadHistory.objects.create)(
                    user=user,
                    video_url=url,
                    video_title=info['title'],
                    platform='youtube',
                    format_label=label,
                    status='completed',
                    file_size=os.path.getsize(file_path),
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
        action = parts[1]  # 'video' or 'audio'
        platform = parts[2]
        url_hash = parts[3]

        await process_download(update, context, url_hash, action, None)
        return
