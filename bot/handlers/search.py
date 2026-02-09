"""Search handlers - Multi-source music search (YouTube + Spotify + Lyrics)."""
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async

from core.models import SearchHistory
from services.search.engine import multi_search_text


def format_duration(seconds):
    """Format duration"""
    if not seconds:
        return '0:00'
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f'{minutes}:{secs:02d}'


def build_search_keyboard(page=0):
    """Build search results keyboard"""
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
    """Format search results"""
    start = page * 10
    page_results = results[start:start + 10]
    lines = []
    for i, track in enumerate(page_results):
        num = start + i + 1
        lines.append(f'{num}. {track["title"]} {format_duration(track.get("duration"))}')
    return '\n'.join(lines)


async def handle_search_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user, query):
    """Handle search request"""
    if not query:
        await update.message.reply_text("Iltimos, qo'shiq nomini yozing.")
        return

    await update.message.reply_text(
        f"🔍 \"{query}\" analiz qilinyapti...\n"
        "1) YouTube Music\n2) Spotify\n3) Lyrics fallback"
    )

    search_result = await asyncio.to_thread(multi_search_text, query)
    total_found = len(search_result.youtube) + len(search_result.spotify) + len(search_result.lyrics)
    await sync_to_async(SearchHistory.objects.create)(
        user=user, query=query, results_count=total_found
    )

    # 1) YouTube results
    if search_result.youtube:
        context.user_data['results'] = search_result.youtube
        context.user_data['page'] = 0
        text = "🎵 YouTube natijalari:\n\n" + format_results(search_result.youtube, page=0)
        await update.message.reply_text(text, reply_markup=build_search_keyboard(page=0))

        # If Spotify also found, share best link (UX: never stop)
        if search_result.spotify and search_result.spotify[0].get("url"):
            best = search_result.spotify[0]
            await update.message.reply_text(
                "✅ Spotify’da ham topildi:\n"
                f"🎧 {best.get('title','')} — {best.get('artist','')}\n"
                f"🔗 {best.get('url')}"
            )
        return

    # 2) Spotify fallback
    if search_result.spotify and search_result.spotify[0].get("url"):
        best = search_result.spotify[0]
        await update.message.reply_text(
            "✅ Spotify’dan topildi:\n"
            f"🎧 {best.get('title','')} — {best.get('artist','')}\n"
            f"🔗 {best.get('url')}\n\n"
            "Agar xohlasangiz, qo‘shiqdan **8–15 soniya** audio/voice yuboring — Shazam orqali aniqlab beraman."
        )
        return

    # 3) Lyrics fallback (YouTube lyrics)
    if search_result.lyrics:
        context.user_data['results'] = search_result.lyrics
        context.user_data['page'] = 0
        text = "📝 Lyrics bo‘yicha topilgan natijalar:\n\n" + format_results(search_result.lyrics, page=0)
        await update.message.reply_text(text, reply_markup=build_search_keyboard(page=0))
        return

    # Nothing found → guide user, never hard-stop
    await update.message.reply_text(
        "Hozircha aniq topa olmadim.\n\n"
        "Quyidagilardan birini yuboring:\n"
        "🎧 Ovozli xabar (8–15 soniya)\n"
        "🎬 Video (qo‘shiq eshitiladigan joyi)\n"
        "🔊 Audio fayl\n\n"
        "Yoki qo‘shiq nomini boshqa variantda yozing (artist + title)."
    )
