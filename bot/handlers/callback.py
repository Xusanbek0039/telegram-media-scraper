"""Callback handlers"""
import asyncio
import os
from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.conf import settings

from core.models import TelegramUser, DownloadHistory, ShazamLog
from django.utils import timezone
from services.downloaders.factory import DownloaderFactory
from services.shazam.service import ShazamService
from .download import process_download
from .search import format_results, build_search_keyboard

DOWNLOADS_DIR = os.path.join(settings.BASE_DIR, 'downloads')
shazam_service = ShazamService()


async def _reply_shazam_from_callback(query, result: dict):
    if result.get("is_successful"):
        text = (
            f"🎵 <b>{result.get('title')}</b>\n"
            f"👤 <b>Ijrochi:</b> {result.get('artist')}\n"
        )
        if result.get("album"):
            text += f"💿 <b>Albom:</b> {result.get('album')}\n"
        if result.get("genre"):
            text += f"🎶 <b>Janr:</b> {result.get('genre')}\n"
        if result.get("shazam_url"):
            text += f"\n🔗 <a href=\"{result.get('shazam_url')}\">Shazam da ochish</a>"
        if result.get("cover"):
            try:
                await query.message.reply_photo(photo=result["cover"], caption=text, parse_mode="HTML")
                return
            except Exception:
                pass
        await query.message.reply_text(text, parse_mode="HTML")
    else:
        await query.message.reply_text(
            f"Qo'shiqni aniqlab bo'lmadi.\n\nSabab: {result.get('error_message', 'Unknown')}"
        )


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

    if data.startswith("music_instagram_"):
        parts = data.split("_", 2)  # music, instagram, hash
        if len(parts) < 3:
            await query.message.reply_text("Xatolik: noto'g'ri callback data.")
            return

        url_hash = parts[2]
        url = context.user_data.get(f"url_{url_hash}")
        if not url:
            await query.message.reply_text("Havola topilmadi. Qayta yuboring.")
            return

        downloader = DownloaderFactory.get_downloader(url)
        if not downloader:
            await query.message.reply_text("Platforma aniqlanmadi.")
            return

        await query.message.reply_text("🎧 Musiqa qidirilmoqda (Shazam)...")

        # Video faylni vaqtincha yuklab olamiz va shazam qilamiz
        tmp_name = f"insta_music_{url_hash}_{query.message.message_id}.mp4"
        tmp_path = os.path.join(DOWNLOADS_DIR, tmp_name)

        file_path = await asyncio.to_thread(downloader.download_video, url, tmp_path, None)
        if not file_path or not os.path.exists(file_path):
            await query.message.reply_text(
                "Video yuklab bo'lmadi. Ko'p hollarda bu ffmpeg yo'qligi sababli bo'ladi.\n"
                "ffmpeg o'rnating va botni qayta ishga tushiring."
            )
            return

        try:
            result = await shazam_service.recognize(file_path)

            # Log
            tg_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=query.from_user.id)
            await sync_to_async(ShazamLog.objects.create)(
                user=tg_user,
                audio_file_name=os.path.basename(file_path),
                recognized_title=result.get("title") if result and result.get("is_successful") else None,
                recognized_artist=result.get("artist") if result and result.get("is_successful") else None,
                is_successful=bool(result and result.get("is_successful")),
                error_message=None if result and result.get("is_successful") else (result.get("error_message") if result else "No result"),
            )

            await _reply_shazam_from_callback(query, result or {"is_successful": False, "error_message": "No result"})
        finally:
            try:
                os.remove(file_path)
            except OSError:
                pass
