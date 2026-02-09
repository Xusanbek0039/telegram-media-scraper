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
from dotenv import load_dotenv

# Load .env file BEFORE Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(env_path)

# Debug: .env faylini tekshirish
if not env_path.exists():
    print(f'[BOT WARNING] .env fayl topilmadi: {env_path}')
else:
    print(f'[BOT INFO] .env fayl topildi: {env_path}')

# Django setup - faqat database uchun
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
    token = None
    
    # 1. Avval .env faylidan o'qib ko'ramiz
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        print('[BOT INFO] Token .env faylidan o\'qildi')
    
    # 2. Agar .env da yo'q bo'lsa, BotSettings dan o'qib ko'ramiz
    if not token:
        try:
            settings = BotSettings.get_settings()
            token = settings.bot_token
            if token:
                print('[BOT INFO] Token BotSettings jadvalidan o\'qildi')
        except Exception as e:
            print(f'[BOT INFO] BotSettings o\'qib bo\'lmadi: {e}')
    
    # 3. Agar hali ham yo'q bo'lsa, Django settings dan o'qib ko'ramiz
    if not token:
        try:
            from django.conf import settings as django_settings
            token = django_settings.TELEGRAM_BOT_TOKEN
            if token:
                print('[BOT INFO] Token Django settings dan o\'qildi')
        except Exception:
            pass
    
    # 4. Token topilmadi
    if not token:
        print('[BOT ERROR] Token topilmadi!')
        print('[BOT INFO] Quyidagilardan birini qiling:')
        print('  1. .env faylida TELEGRAM_BOT_TOKEN ni kiriting')
        print('  2. Admin panelda BotSettings yarating va token kiriting')
        print(f'[DEBUG] .env fayl yo\'li: {BASE_DIR / ".env"}')
        print(f'[DEBUG] .env fayl mavjudmi: {(BASE_DIR / ".env").exists()}')
        if (BASE_DIR / '.env').exists():
            print(f'[DEBUG] .env fayl mazmuni:')
            try:
                with open(BASE_DIR / '.env', 'r') as f:
                    content = f.read()
                    # Token qismini yashirish
                    lines = content.split('\n')
                    for line in lines:
                        if 'TELEGRAM_BOT_TOKEN' in line:
                            print(f'  {line[:30]}... (token yashirildi)')
                        else:
                            print(f'  {line}')
            except Exception as e:
                print(f'  [ERROR] O\'qib bo\'lmadi: {e}')
        sys.exit(1)
    
    # 5. BotSettings dan enabled holatini tekshiramiz (agar mavjud bo'lsa)
    try:
        settings = BotSettings.get_settings()
        if not settings.is_bot_enabled:
            print('[BOT INFO] Bot hozircha o\'chirilgan. Admin panelda yoqing.')
            sys.exit(0)
    except Exception:
        pass  # BotSettings yo'q bo'lsa, davom etamiz

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
