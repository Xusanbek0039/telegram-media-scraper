# ⚡ Tezkor Boshlash

## 5 daqiqada ishga tushirish

### 1. O'rnatish
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

### 2. Bot token sozlash

**Variant A: Admin panel orqali (Tavsiya etiladi)**
1. `python manage.py runserver`
2. `/admin/core/botsettings/add/` ga o'ting
3. Token kiriting va saqlang

**Variant B: .env orqali**
`.env` faylida `TELEGRAM_BOT_TOKEN` ni kiriting

### 3. Ishga tushirish

**Terminal 1:**
```bash
python manage.py runserver
```

**Terminal 2:**
```bash
python bot/run_bot.py
```

Yoki Windows:
```cmd
start_bot.bat
```

### 4. Test qiling

Telegram'da botga `/start` yuboring!

## 📋 Checklist

- [ ] Requirements o'rnatildi
- [ ] Migration qilindi
- [ ] Superuser yaratildi
- [ ] Bot token sozlandi (Admin panel yoki .env)
- [ ] Django ishlamoqda
- [ ] Bot ishlamoqda
- [ ] Test qilindi

## 🎯 Keyingi qadamlar

1. Admin panelda Analytics'ni ko'ring: `/admin/analytics/`
2. Bot Settings'ni sozlang: `/admin/core/botsettings/1/change/`
3. Foydalanuvchilarni ko'ring: `/admin/core/telegramuser/`

## ❓ Muammo?

- Bot ishlamayapti? → BotSettings da token tekshiring
- Database xatolik? → `python manage.py migrate`
- Import xatolik? → `__pycache__` ni o'chiring
