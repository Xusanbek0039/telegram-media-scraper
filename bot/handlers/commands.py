"""Command handlers"""
from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async

from core.models import TelegramUser


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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
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
