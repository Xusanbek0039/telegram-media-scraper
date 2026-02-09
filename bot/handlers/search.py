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
    """Format duration"""
    if not seconds:
        return '0:00'
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f'{minutes}:{secs:02d}'


def build_search_keyboard(results, page=0):
    """Build search results keyboard"""
    start = page * 5
    page_results = results[start:start + 5]
    total_pages = (len(results) + 4) // 5

    rows = []
    for i in range(len(page_results)):
        idx = start + i
        track = page_results[i]
        title = track.get("title", "")[:30]
        dur = format_duration(track.get("duration"))
        btn_text = f"{idx + 1}. {title} [{dur}]"
        rows.append([InlineKeyboardButton(btn_text, callback_data=f'select_{idx}')])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton('⬅️ Oldingi', callback_data=f'page_{page - 1}'))
    nav_row.append(InlineKeyboardButton('❌ Bekor', callback_data='cancel'))
    if (page + 1) < total_pages:
        nav_row.append(InlineKeyboardButton('Keyingi ➡️', callback_data=f'page_{page + 1}'))
    rows.append(nav_row)

    return InlineKeyboardMarkup(rows)


def format_results(results, page=0):
    """Format search results"""
    start = page * 5
    page_results = results[start:start + 5]
    total_pages = (len(results) + 4) // 5
    lines = [f"📄 Sahifa {page + 1}/{total_pages}\n"]
    for i, track in enumerate(page_results):
        num = start + i + 1
        artist = track.get("artist", "")
        title = track.get("title", "Noma'lum")
        dur = format_duration(track.get("duration"))
        if artist:
            lines.append(f'{num}. 🎵 {title}\n   👤 {artist} | ⏱ {dur}')
        else:
            lines.append(f'{num}. 🎵 {title} | ⏱ {dur}')
    return '\n'.join(lines)


async def handle_search_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user, query):
    """Handle search request"""
    if not query:
        await update.message.reply_text("Iltimos, qo'shiq nomini yozing.")
        return

    status_msg = await update.message.reply_text(
        f"🔍 \"{query}\" qidirilmoqda...\n"
        "⏳ Biroz kuting..."
    )

    try:
        search_result = await asyncio.to_thread(multi_search_text, query)
    except Exception as e:
        logger.error("Search error: %s", e)
        await status_msg.edit_text(
            "Qidirishda xatolik yuz berdi. Qaytadan urinib ko'ring."
        )
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
        text = "🎵 YouTube natijalar:\n\n" + format_results(search_result.youtube, page=0)
        text += "\n\n👇 Qo'shiqni tanlang — audio yuklab beriladi"
        await update.message.reply_text(
            text, reply_markup=build_search_keyboard(search_result.youtube, page=0)
        )

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
        text = "📝 Lyrics bo'yicha topildi:\n\n" + format_results(search_result.lyrics, page=0)
        text += "\n\n👇 Qo'shiqni tanlang — audio yuklab beriladi"
        await update.message.reply_text(
            text, reply_markup=build_search_keyboard(search_result.lyrics, page=0)
        )
        return

    await update.message.reply_text(
        f"❌ \"{query}\" bo'yicha hech narsa topilmadi.\n\n"
        "💡 Maslahatlar:\n"
        "• Artist nomi + qo'shiq nomi yozing\n"
        "• Inglizcha yoki ruscha yozib ko'ring\n"
        "• Ovozli xabar yuboring (Shazam orqali aniqlanadi)"
    )
