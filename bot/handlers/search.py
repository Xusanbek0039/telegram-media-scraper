"""Search handlers - Multi-source music search (YouTube + Spotify + Lyrics)."""
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async

from core.models import SearchHistory
from services.search.engine import multi_search_text

logger = logging.getLogger(__name__)


def format_duration(seconds):
    if not seconds:
        return '0:00'
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f'{minutes}:{secs:02d}'


def build_search_keyboard(page=0):
    start = page * 10
    row1 = [InlineKeyboardButton(str(start + i + 1), callback_data=f'select_{start + i}') for i in range(5)]
    row2 = [InlineKeyboardButton(str(start + i + 6), callback_data=f'select_{start + i + 5}') for i in range(5)]
    row3 = [
        InlineKeyboardButton('⬅️', callback_data=f'page_{page - 1}'),
        InlineKeyboardButton('❌', callback_data='cancel'),
        InlineKeyboardButton('➡️', callback_data=f'page_{page + 1}'),
    ]
    return InlineKeyboardMarkup([row1, row2, row3])


def format_results(results, page=0):
    start = page * 10
    page_results = results[start:start + 10]
    lines = []
    for i, track in enumerate(page_results):
        num = start + i + 1
        title = track.get("title", "Noma'lum")
        dur = format_duration(track.get("duration"))
        lines.append(f'{num}. {title} {dur}')
    return '\n'.join(lines)


async def handle_search_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user, query):
    if not query:
        await update.message.reply_text("Iltimos, qo'shiq nomini yozing.")
        return

    status_msg = await update.message.reply_text(
        f"🔍 \"{query}\" qidirilmoqda...\n⏳ Biroz kuting..."
    )

    try:
        search_result = await asyncio.to_thread(multi_search_text, query)
    except Exception as e:
        logger.error("Search error: %s", e)
        await status_msg.edit_text("Qidirishda xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return

    total_found = len(search_result.youtube) + len(search_result.spotify) + len(search_result.lyrics)

    try:
        await sync_to_async(SearchHistory.objects.create)(
            user=user, query=query, results_count=total_found
        )
    except Exception as e:
        logger.warning("SearchHistory save error: %s", e)

    try:
        await status_msg.delete()
    except Exception:
        pass

    if search_result.youtube:
        context.user_data['results'] = search_result.youtube
        context.user_data['page'] = 0
        text = format_results(search_result.youtube, page=0)
        await update.message.reply_text(text, reply_markup=build_search_keyboard(page=0))

        if search_result.spotify and search_result.spotify[0].get("url"):
            best = search_result.spotify[0]
            await update.message.reply_text(
                "🟢 Spotify'da ham topildi:\n"
                f"🎧 {best.get('title', '')} — {best.get('artist', '')}\n"
                f"🔗 {best.get('url')}"
            )
        return

    if search_result.spotify and search_result.spotify[0].get("url"):
        best = search_result.spotify[0]
        await update.message.reply_text(
            "🟢 Spotify'dan topildi:\n"
            f"🎧 {best.get('title', '')} — {best.get('artist', '')}\n"
            f"🔗 {best.get('url')}\n\n"
            "YouTube'dan topolmadim. Boshqa variant bilan yozing."
        )
        return

    if search_result.lyrics:
        context.user_data['results'] = search_result.lyrics
        context.user_data['page'] = 0
        text = format_results(search_result.lyrics, page=0)
        await update.message.reply_text(text, reply_markup=build_search_keyboard(page=0))
        return

    await update.message.reply_text(
        f"❌ \"{query}\" bo'yicha hech narsa topilmadi.\n\n"
        "💡 Maslahatlar:\n"
        "• Artist nomi + qo'shiq nomi yozing\n"
        "• Inglizcha yoki ruscha yozib ko'ring\n"
        "• Ovozli xabar yuboring (Shazam orqali aniqlanadi)"
    )
