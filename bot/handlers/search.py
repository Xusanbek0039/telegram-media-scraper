"""Search handlers - YouTube search"""
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async

from core.models import SearchHistory


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


def search_youtube(query, limit=10):
    """Search YouTube"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': f'ytsearch{limit}',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(query, download=False)
            entries = result.get('entries', [])
            results = []
            for entry in entries:
                if entry:
                    results.append({
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Noma\'lum'),
                        'duration': entry.get('duration', 0),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    })
            return results
        except Exception:
            return []


async def handle_search_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user, query):
    """Handle search request"""
    if not query:
        await update.message.reply_text("Iltimos, qo'shiq nomini yozing.")
        return

    await update.message.reply_text(f"🔍 \"{query}\" qidirilmoqda...")
    results = await asyncio.to_thread(search_youtube, query)
    await sync_to_async(SearchHistory.objects.create)(
        user=user, query=query, results_count=len(results)
    )

    if not results:
        await update.message.reply_text(
            f"\"{query}\" bo'yicha hech narsa topilmadi.\nBoshqa nom bilan qidirib ko'ring."
        )
        return

    context.user_data['results'] = results
    context.user_data['page'] = 0
    text = format_results(results, page=0)
    await update.message.reply_text(text, reply_markup=build_search_keyboard(page=0))
