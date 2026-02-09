# Telegram Musiqa Qidiruv Bot

Django frameworkida yaratilgan Telegram bot. Foydalanuvchi musiqa nomini yozsa, bot iTunes orqali qo'shiqlarni topib beradi.

## Imkoniyatlar

- Musiqa nomini yozib qidirish
- Artis va albom ma'lumotlarini ko'rsatish
- Qo'shiq preview'ini yuborish
- Django admin panelda foydalanuvchilar va qidiruv tarixini ko'rish

## O'rnatish

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
copy .env.example .env
```

`.env` faylini tahrirlang va quyidagi qiymatlarni kiriting:

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

### 6. Botni ishga tushirish

```bash
python manage.py runbot
```

### 7. Admin panelga kirish

Django serverni ishga tushiring:

```bash
python manage.py runserver
```

Brauzerda oching: http://127.0.0.1:8000/admin/

## Loyiha tuzilishi

```
telegram-media-scraper/
├── config/              # Django sozlamalari
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── bot/                 # Bot ilovasi
│   ├── models.py        # TelegramUser, SearchHistory
│   ├── admin.py         # Admin panel sozlamalari
│   └── management/
│       └── commands/
│           └── runbot.py  # Bot ishga tushirish buyrug'i
├── manage.py
├── requirements.txt
└── .env.example
```
