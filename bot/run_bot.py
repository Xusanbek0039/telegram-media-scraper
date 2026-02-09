#!/usr/bin/env python
"""
Independent Telegram Bot Runner
Bot Django'dan mustaqil ishlaydi, faqat database orqali bog'lanadi
"""
import os
import sys
import asyncio
import django
from pathlib import Path

# Django setup - faqat database uchun
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import Update

from bot.handlers.commands import start_command
from bot.handlers.message import handle_message
from bot.handlers.shazam import handle_voice, handle_video, handle_audio_file
from bot.handlers.callback import callback_handler
from core.models import BotSettings


def main():
    """Run Telegram bot independently"""
    # Get bot settings from database
    try:
        settings = BotSettings.get_settings()
        token = settings.bot_token
        
        if not token:
            print('[BOT ERROR] Bot token topilmadi! BotSettings jadvalidan token kiriting.')
            sys.exit(1)
            
        if not settings.is_bot_enabled:
            print('[BOT INFO] Bot hozircha o\'chirilgan. Admin panelda yoqing.')
            sys.exit(0)
            
    except Exception as e:
        print(f'[BOT ERROR] BotSettings o\'qib bo\'lmadi: {e}')
        print('[BOT INFO] .env faylidan token o\'qilmoqda...')
        from django.conf import settings as django_settings
        token = django_settings.TELEGRAM_BOT_TOKEN
        
        if not token:
            print('[BOT ERROR] Token topilmadi! .env yoki BotSettings da token kiriting.')
            sys.exit(1)

    # Create application
    app = Application.builder().token(token).build()

    # Register handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, handle_video))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print('[BOT] Telegram bot ishga tushdi!')
    print('[BOT] Bot Django\'dan mustaqil ishlayapti, faqat database orqali bog\'langan.')
    
    # Run bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
