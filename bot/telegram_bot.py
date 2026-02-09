"""
Legacy file - kept for backward compatibility
Use bot/run_bot.py instead for independent bot runner
"""
import warnings

warnings.warn(
    "bot.telegram_bot is deprecated. Use bot.run_bot module instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from new structure for backward compatibility
from bot.handlers.commands import start_command
from bot.handlers.message import handle_message
from bot.handlers.shazam import handle_voice, handle_video, handle_audio_file
from bot.handlers.callback import callback_handler

__all__ = [
    'start_command',
    'handle_message',
    'handle_voice',
    'handle_video',
    'handle_audio_file',
    'callback_handler',
]
