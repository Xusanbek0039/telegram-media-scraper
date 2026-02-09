from django.apps import AppConfig


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'
    verbose_name = 'Telegram Bot'

    # Bot Django ichidan ishga tushirilmaydi.
    # Botni alohida ishga tushiring: python bot/run_bot.py
