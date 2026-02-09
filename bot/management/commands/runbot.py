from django.core.management.base import BaseCommand
from bot.telegram_bot import _run_bot


class Command(BaseCommand):
    help = 'Telegram botni ishga tushirish'

    def handle(self, *args, **options):
        _run_bot()
