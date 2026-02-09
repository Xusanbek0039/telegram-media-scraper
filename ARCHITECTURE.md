# 🏗️ Arxitektura Hujjati

## Asosiy Prinsiplar

### 1. Separation of Concerns

- **Django** - Faqat admin panel va database
- **Bot** - Faqat foydalanuvchi interfeysi (router)
- **Services** - Og'ir ishlar (download, recognition)

### 2. Independence

- Django botni start qilmaydi
- Bot Djangoga to'g'ridan-to'g'ri bog'lanmaydi
- Ikkalasi faqat DATABASE orqali gaplashadi

### 3. Scalability

- Har platforma alohida modul
- Queue mentality (keyinchalik Redis/Celery qo'shish oson)
- Service-based architecture

## 📦 Modullar

### Core (`core/`)

**Vazifasi:** Umumiy modellar va utilities

- `TelegramUser` - Foydalanuvchi ma'lumotlari
- `DownloadHistory` - Yuklash tarixi
- `ShazamLog` - Shazam loglari
- `BotSettings` - Bot sozlamalari
- `Broadcast` - Reklama

### Bot (`bot/`)

**Vazifasi:** Faqat routing va foydalanuvchi bilan muloqot

**Struktura:**
- `handlers/commands.py` - /start va boshqa commandlar
- `handlers/message.py` - Text message routing
- `handlers/download.py` - Download request routing
- `handlers/search.py` - YouTube search
- `handlers/shazam.py` - Shazam request routing
- `handlers/callback.py` - Callback query handling
- `run_bot.py` - Mustaqil bot runner

**Qoida:** Bot hech qachon:
- ❌ Download qilmaydi
- ❌ Audio tanimaydi
- ❌ Video convert qilmaydi

Bot faqat:
- ✅ Message qabul qiladi
- ✅ Platformani aniqlaydi
- ✅ Servicega yuboradi
- ✅ Natijani jo'natadi

### Services (`services/`)

**Vazifasi:** Og'ir ishlar

#### Downloaders (`services/downloaders/`)

Har platforma alohida service:

- `youtube_service.py` - YouTube downloader
- `instagram_service.py` - Instagram downloader
- `tiktok_service.py` - TikTok downloader
- `snapchat_service.py` - Snapchat downloader
- `likee_service.py` - Likee downloader
- `factory.py` - Platforma aniqlash va service qaytarish

**BaseDownloader interface:**
```python
- detect(url) -> bool
- get_info(url) -> Dict
- download_video(url, output_path, quality) -> str
- download_audio(url, output_path) -> str
- get_available_qualities(url) -> List[Dict]
```

#### Shazam (`services/shazam/`)

- `service.py` - Audio recognition service

## 🔄 Data Flow

### Download Request:

```
User → Bot (message handler)
  ↓
Bot → DownloaderFactory.detect_platform()
  ↓
Bot → DownloaderService.get_info()
  ↓
Bot → User (quality selection)
  ↓
User → Bot (callback)
  ↓
Bot → DownloaderService.download_video/audio()
  ↓
Bot → Database (DownloadHistory)
  ↓
Bot → User (file)
```

### Shazam Request:

```
User → Bot (voice/video handler)
  ↓
Bot → ShazamService.recognize()
  ↓
Bot → Database (ShazamLog)
  ↓
Bot → User (result)
```

## 🗄️ Database Schema

### TelegramUser
- telegram_id (unique)
- username, first_name, last_name
- download_count
- is_premium
- is_banned

### DownloadHistory
- user (FK)
- video_url
- video_title
- platform (youtube, instagram, ...)
- format_label
- status (pending, processing, completed, failed)
- file_size
- error_message

### ShazamLog
- user (FK)
- audio_file_name
- recognized_title
- recognized_artist
- is_successful
- error_message

### BotSettings
- is_bot_enabled
- bot_token
- max_file_size_mb
- rate_limit_per_minute
- maintenance_message

## 🚀 Deployment

### Local Development:

```bash
# Terminal 1
python manage.py runserver

# Terminal 2
python bot/run_bot.py
```

### Production:

**Django (WSGI):**
- Gunicorn
- Passenger
- uWSGI

**Bot (Worker):**
- nohup
- systemd service
- supervisor

**Database:**
- PostgreSQL (recommended)
- MySQL
- SQLite (development only)

## 🔮 Keyingi qadamlar (Scalability)

1. **Queue System:**
   - Redis + Celery
   - Download tasks queue
   - Async processing

2. **Caching:**
   - Redis cache
   - Video info caching
   - User data caching

3. **Monitoring:**
   - Sentry (error tracking)
   - Prometheus (metrics)
   - Logging

4. **Load Balancing:**
   - Multiple bot workers
   - Database replication
   - CDN for static files
