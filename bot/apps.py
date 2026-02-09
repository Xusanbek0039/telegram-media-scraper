import os
from django.apps import AppConfig


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'
    verbose_name = 'Telegram Bot'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            from bot.telegram_bot import start_bot
            start_bot()
