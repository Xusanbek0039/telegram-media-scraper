# Telegram Media Scraper Bot

Senior-level arxitekturaga ega Telegram media downloader va Shazam bot.

## 🏗️ Arxitektura

Loyiha 3 ta mustaqil qismga ajratilgan:

1. **Django Core** - Admin Panel + Database
2. **Telegram Bot** - User Interface (faqat router)
3. **Processing Services** - Downloader + Shazam

### 📁 Papka strukturi

```
project/
│
├── config/          → Django settings
├── core/            → umumiy model va utils
│   ├── models.py    → TelegramUser, DownloadHistory, ShazamLog, BotSettings
│   └── admin.py     → Admin panel
│
├── bot/             → telegram logika (faqat routing)
│    ├── handlers/   → Message handlers
│    │   ├── commands.py
│    │   ├── message.py
│    │   ├── download.py
│    │   ├── search.py
│    │   ├── shazam.py
│    │   └── callback.py
│    └── run_bot.py  → Mustaqil bot runner
│
├── services/
│    ├── downloaders/ → Platform-specific downloaders
│    │   ├── youtube_service.py
│    │   ├── instagram_service.py
│    │   ├── tiktok_service.py
│    │   ├── snapchat_service.py
│    │   ├── likee_service.py
│    │   └── factory.py
│    └── shazam/     → Audio recognition
│        └── service.py
│
└── manage.py
```

## 🚀 O'rnatish

### 1. Virtual muhit yaratish

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# yoki
source venv/bin/activate  # Linux/Mac
```

### 2. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 3. `.env` faylini sozlash

`.env.example` faylidan nusxa oling:

```bash
copy .env.example .env  # Windows
# yoki
cp .env.example .env    # Linux/Mac
```

`.env` faylini tahrirlang:

- `TELEGRAM_BOT_TOKEN` — @BotFather dan olingan bot token
- `SECRET_KEY` — Django secret key

### 4. Ma'lumotlar bazasini yaratish

```bash
python manage.py migrate
```

### 5. Admin foydalanuvchi yaratish

```bash
python manage.py createsuperuser
```

### 6. Bot sozlamalarini yaratish

Admin panelga kirib (`/admin/core/botsettings/add/`), BotSettings yarating va token kiriting.

## ▶️ Ishga tushirish

### ⚠️ MUHIM: Bot va Django alohida ishlaydi!

**Terminal 1 - Django Admin Panel:**
```bash
python manage.py runserver
```

**Terminal 2 - Telegram Bot:**
```bash
python bot/run_bot.py
```

Yoki Windows PowerShell:
```powershell
python bot\run_bot.py
```

### Serverda (Production)

**Django (Gunicorn/Passenger):**
```bash
gunicorn config.wsgi:application
```

**Bot (nohup/systemd):**
```bash
nohup python bot/run_bot.py > bot.log 2>&1 &
```

Yoki systemd service yarating.

## 📊 Admin Panel

Admin panelda quyidagi bo'limlar mavjud:

- **Bot Settings** - Bot sozlamalari (ON/OFF, Token, Rate limit)
- **Users** - Foydalanuvchilar (Premium, Ban)
- **Download History** - Yuklash tarixi (Platforma, Status)
- **Shazam Logs** - Shazam aniqlash tarixi
- **Analytics** - Statistikalar (`/admin/analytics/`)
- **Broadcast** - Reklama yuborish

## 🎯 Qanday ishlaydi?

### Download Flow:

1. User link yuboradi → Bot
2. Bot → Platformani aniqlaydi (`DownloaderFactory`)
3. Bot → Servicega yuboradi (`services/downloaders/`)
4. Service → Video/Audio yuklaydi
5. Bot → Natijani jo'natadi

### Shazam Flow:

1. User audio yuboradi → Bot
2. Bot → Shazam servicega yuboradi (`services/shazam/`)
3. Service → Audio aniqlaydi
4. Bot → Natijani jo'natadi

## 🔧 Qo'shish yangi platforma

`services/downloaders/` papkasida yangi service yarating:

```python
from .base import BaseDownloader

class NewPlatformService(BaseDownloader):
    def detect(self, url: str) -> bool:
        # URL aniqlash logikasi
        pass
    
    def get_info(self, url: str) -> Optional[Dict]:
        # Video ma'lumotlari
        pass
    
    # ... boshqa metodlar
```

Keyin `factory.py` ga qo'shing.

## 📝 Migration qilish

Agar eski versiyadan ko'chiryapsiz:

1. Database backup oling
2. Yangi kodni o'rnating
3. Migration qiling:
```bash
python manage.py makemigrations
python manage.py migrate
```

## 🐛 Troubleshooting

**Bot ishlamayapti:**
- BotSettings da token to'g'ri kiritilganligini tekshiring
- Bot enabled ekanligini tekshiring
- `.env` faylida token borligini tekshiring

**Download ishlamayapti:**
- `yt-dlp` yangi versiyasini o'rnating
- Platforma API o'zgargan bo'lishi mumkin

**Database xatolik:**
- Migration qiling: `python manage.py migrate`

## 📄 License

MIT
