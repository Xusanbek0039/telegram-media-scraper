"""Shazam handlers - routes to Shazam service"""
import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone

from core.models import TelegramUser, ShazamLog
from services.shazam.service import ShazamService

DOWNLOADS_DIR = os.path.join(settings.BASE_DIR, 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

shazam_service = ShazamService()


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


async def send_shazam_result(update: Update, result: dict, file_name: str, user):
    """Send Shazam recognition result"""
    if result.get('is_successful'):
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

        # Save successful log
        await sync_to_async(ShazamLog.objects.create)(
            user=user,
            audio_file_name=file_name,
            recognized_title=result['title'],
            recognized_artist=result['artist'],
            is_successful=True,
        )

        if result.get('cover'):
            try:
                await update.message.reply_photo(
                    photo=result['cover'], caption=text, parse_mode='HTML'
                )
                return
            except Exception:
                pass
        await update.message.reply_text(text, parse_mode='HTML')
    else:
        # Save failed log
        await sync_to_async(ShazamLog.objects.create)(
            user=user,
            audio_file_name=file_name,
            is_successful=False,
            error_message=result.get('error_message', 'Unknown error'),
        )
        await update.message.reply_text("Qo'shiqni aniqlab bo'lmadi. Qaytadan urinib ko'ring.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice message"""
    user = await save_user(update.effective_user)
    await update.message.reply_text("🎤 Qo'shiq aniqlanmoqda...")

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    file = await context.bot.get_file(voice.file_id)
    tmp = os.path.join(DOWNLOADS_DIR, f'shazam_{update.message.message_id}.ogg')
    await file.download_to_drive(tmp)

    try:
        result = await shazam_service.recognize(tmp)
        if result:
            await send_shazam_result(update, result, f'shazam_{update.message.message_id}.ogg', user)
        else:
            await send_shazam_result(
                update,
                {'is_successful': False, 'error_message': 'No result'},
                f'shazam_{update.message.message_id}.ogg',
                user
            )
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video message"""
    user = await save_user(update.effective_user)
    await update.message.reply_text("🎤 Qo'shiq aniqlanmoqda...")

    video = update.message.video or update.message.video_note
    if not video:
        return

    file = await context.bot.get_file(video.file_id)
    tmp = os.path.join(DOWNLOADS_DIR, f'shazam_video_{update.message.message_id}.mp4')
    await file.download_to_drive(tmp)

    try:
        result = await shazam_service.recognize(tmp)
        if result:
            await send_shazam_result(update, result, f'shazam_video_{update.message.message_id}.mp4', user)
        else:
            await send_shazam_result(
                update,
                {'is_successful': False, 'error_message': 'No result'},
                f'shazam_video_{update.message.message_id}.mp4',
                user
            )
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


async def handle_audio_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle audio file"""
    user = await save_user(update.effective_user)
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
        result = await shazam_service.recognize(tmp)
        if result:
            await send_shazam_result(update, result, f'shazam_audio_{update.message.message_id}.{ext}', user)
        else:
            await send_shazam_result(
                update,
                {'is_successful': False, 'error_message': 'No result'},
                f'shazam_audio_{update.message.message_id}.{ext}',
                user
            )
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
