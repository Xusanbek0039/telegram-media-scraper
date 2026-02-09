# 🔄 Migration Guide (Eski versiyadan)

Agar sizda eski versiya bo'lsa va yangi strukturaga ko'chirmoqchi bo'lsangiz:

## 1. Backup oling

```bash
# Database backup
python manage.py dumpdata > backup.json

# Yoki SQLite uchun
copy db.sqlite3 db.sqlite3.backup
```

## 2. Yangi kodni o'rnating

Git orqali:
```bash
git pull origin main
```

Yoki qo'lda yangi fayllarni ko'chiring.

## 3. Migration qiling

```bash
# Yangi migrationlar yaratish
python manage.py makemigrations core

# Migration qilish
python manage.py migrate
```

## 4. Bot sozlamalarini yarating

Admin panelga kiring va `/admin/core/botsettings/add/` ga o'ting.

Yoki Python shell orqali:
```python
python manage.py shell
```

```python
from core.models import BotSettings
from django.conf import settings

BotSettings.objects.create(
    pk=1,
    is_bot_enabled=True,
    bot_token=settings.TELEGRAM_BOT_TOKEN,
    max_file_size_mb=50,
    rate_limit_per_minute=10,
)
```

## 5. Eski management commandni o'chiring

Eski `python manage.py runbot` endi ishlamaydi.

Buning o'rniga:
```bash
python bot/run_bot.py
```

## 6. Test qiling

1. Django admin panelni oching: `http://127.0.0.1:8000/admin/`
2. Botni ishga tushiring: `python bot/run_bot.py`
3. Botga /start yuboring

## ⚠️ Muhim o'zgarishlar

### Model o'zgarishlari:

- `TelegramUser` endi `download_count`, `is_premium`, `is_banned` maydonlariga ega
- `DownloadHistory` endi `platform`, `status`, `file_size`, `error_message` maydonlariga ega
- Yangi model: `ShazamLog`
- Yangi model: `BotSettings`

### Kod o'zgarishlari:

- Barcha modellar `core.models` ga ko'chirildi
- Bot logika `bot/handlers/` ga ajratildi
- Download logika `services/downloaders/` ga ko'chirildi
- Shazam logika `services/shazam/` ga ko'chirildi

### Admin panel:

- Endi `core.*` modellar admin panelda
- Analytics sahifa: `/admin/analytics/`
- Bot Settings: `/admin/core/botsettings/1/change/`

## 🐛 Muammolar

**ImportError: cannot import from bot.models**
- `bot/models.py` endi `core.models` dan import qiladi
- Agar muammo bo'lsa, Python cache'ni tozalang:
```bash
find . -type d -name __pycache__ -exec rm -r {} +
find . -name "*.pyc" -delete
```

**Bot ishlamayapti**
- BotSettings yaratilganligini tekshiring
- Token to'g'ri kiritilganligini tekshiring
- `.env` faylida token borligini tekshiring

**Database xatolik**
- Migration qiling: `python manage.py migrate`
- Agar migration xatolik bersa, `--fake` flag ishlating (ehtiyotkorlik bilan!)
