from django.db import models


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, verbose_name='Telegram ID')
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name='Username')
    first_name = models.CharField(max_length=255, verbose_name='Ism')
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Familiya')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ro\'yxatdan o\'tgan vaqt')
    last_active = models.DateTimeField(auto_now=True, verbose_name='Oxirgi faollik')
    download_count = models.PositiveIntegerField(default=0, verbose_name='Yuklashlar soni')
    is_premium = models.BooleanField(default=False, verbose_name='Premium')
    is_banned = models.BooleanField(default=False, verbose_name='Bloklangan')

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'
        ordering = ['-last_active']

    def __str__(self):
        if self.username:
            return f'@{self.username}'
        return self.first_name


class SearchHistory(models.Model):
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='searches',
        verbose_name='Foydalanuvchi',
    )
    query = models.CharField(max_length=500, verbose_name='Qidiruv so\'rovi')
    results_count = models.IntegerField(default=0, verbose_name='Natijalar soni')
    searched_at = models.DateTimeField(auto_now_add=True, verbose_name='Qidirilgan vaqt')

    class Meta:
        verbose_name = 'Qidiruv tarixi'
        verbose_name_plural = 'Qidiruv tarixi'
        ordering = ['-searched_at']

    def __str__(self):
        return f'{self.user} - "{self.query}"'


class DownloadHistory(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('processing', 'Ishlanmoqda'),
        ('completed', 'Yakunlandi'),
        ('failed', 'Xatolik'),
    ]

    PLATFORM_CHOICES = [
        ('youtube', 'YouTube'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('snapchat', 'Snapchat'),
        ('likee', 'Likee'),
        ('other', 'Boshqa'),
    ]

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='downloads',
        verbose_name='Foydalanuvchi',
    )
    video_url = models.URLField(max_length=500, verbose_name='Video havolasi')
    video_title = models.CharField(max_length=500, verbose_name='Video nomi')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='other', verbose_name='Platforma')
    format_label = models.CharField(max_length=50, verbose_name='Format')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Holat')
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name='Fayl hajmi (bayt)')
    error_message = models.TextField(blank=True, null=True, verbose_name='Xatolik xabari')
    downloaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Yuklangan vaqt')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Yakunlangan vaqt')

    class Meta:
        verbose_name = 'Yuklash tarixi'
        verbose_name_plural = 'Yuklash tarixi'
        ordering = ['-downloaded_at']

    def __str__(self):
        return f'{self.user} - {self.video_title} ({self.format_label})'


class ShazamLog(models.Model):
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='shazam_logs',
        verbose_name='Foydalanuvchi',
    )
    audio_file_name = models.CharField(max_length=255, verbose_name='Audio fayl nomi')
    recognized_title = models.CharField(max_length=500, blank=True, null=True, verbose_name='Aniqlangan qo\'shiq')
    recognized_artist = models.CharField(max_length=500, blank=True, null=True, verbose_name='Aniqlangan ijrochi')
    is_successful = models.BooleanField(default=False, verbose_name='Muvaffaqiyatli')
    error_message = models.TextField(blank=True, null=True, verbose_name='Xatolik xabari')
    recognized_at = models.DateTimeField(auto_now_add=True, verbose_name='Aniqlangan vaqt')

    class Meta:
        verbose_name = 'Shazam log'
        verbose_name_plural = 'Shazam loglar'
        ordering = ['-recognized_at']

    def __str__(self):
        if self.is_successful:
            return f'{self.user} - {self.recognized_title} by {self.recognized_artist}'
        return f'{self.user} - Aniqlanmadi'


class Broadcast(models.Model):
    SEND_TYPE_CHOICES = [
        ('once', 'Bir marta'),
        ('repeat', 'Takroriy'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('sending', 'Yuborilmoqda'),
        ('sent', 'Yuborildi'),
        ('failed', 'Xatolik'),
    ]

    message = models.TextField(verbose_name='Xabar matni')
    photo = models.ImageField(upload_to='broadcasts/', blank=True, null=True, verbose_name='Rasm')
    send_type = models.CharField(max_length=10, choices=SEND_TYPE_CHOICES, default='once', verbose_name='Yuborish turi')
    repeat_hours = models.PositiveIntegerField(default=0, verbose_name='Har necha soatda (takroriy)', help_text='Faqat takroriy yuborish uchun')
    is_active = models.BooleanField(default=True, verbose_name='Faolmi')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Holat')
    sent_count = models.PositiveIntegerField(default=0, verbose_name='Yuborilganlar soni')
    failed_count = models.PositiveIntegerField(default=0, verbose_name='Xatoliklar soni')
    last_sent_at = models.DateTimeField(blank=True, null=True, verbose_name='Oxirgi yuborilgan vaqt')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqt')

    class Meta:
        verbose_name = 'Reklama'
        verbose_name_plural = 'Reklamalar'
        ordering = ['-created_at']

    def __str__(self):
        return f'Reklama #{self.pk} - {self.get_status_display()}'


class BotSettings(models.Model):
    """Bot sozlamalari - faqat bitta instance bo'lishi kerak"""
    is_bot_enabled = models.BooleanField(default=True, verbose_name='Bot faolmi')
    bot_token = models.CharField(max_length=255, verbose_name='Bot Token', help_text='Telegram bot token')
    max_file_size_mb = models.PositiveIntegerField(default=50, verbose_name='Maksimal fayl hajmi (MB)')
    rate_limit_per_minute = models.PositiveIntegerField(default=10, verbose_name='Har minutda maksimal so\'rovlar')
    maintenance_message = models.TextField(blank=True, verbose_name='Texnik xizmat xabari')
    is_maintenance_mode = models.BooleanField(default=False, verbose_name='Texnik xizmat rejimi')
    youtube_enabled = models.BooleanField(default=True, verbose_name='YouTube yoqilganmi')
    instagram_enabled = models.BooleanField(default=True, verbose_name='Instagram yoqilganmi')
    tiktok_enabled = models.BooleanField(default=True, verbose_name='TikTok yoqilganmi')
    snapchat_enabled = models.BooleanField(default=True, verbose_name='Snapchat yoqilganmi')
    likee_enabled = models.BooleanField(default=True, verbose_name='Likee yoqilganmi')
    parallel_download_limit = models.PositiveIntegerField(default=3, verbose_name='Parallel yuklab olish limiti')
    shazam_daily_limit = models.PositiveIntegerField(default=20, verbose_name='Shazam kunlik limit')
    shazam_max_audio_length = models.PositiveIntegerField(default=60, verbose_name='Shazam maks audio uzunligi (soniya)')
    free_daily_download_limit = models.PositiveIntegerField(default=5, verbose_name='Bepul kunlik yuklab olish limiti')
    premium_daily_download_limit = models.PositiveIntegerField(default=100, verbose_name='Premium kunlik yuklab olish limiti')
    ad_revenue_per_view = models.DecimalField(max_digits=10, decimal_places=4, default=0, verbose_name='Reklama daromadi (ko\u02BBrishga)')

    class Meta:
        verbose_name = 'Bot sozlamalari'
        verbose_name_plural = 'Bot sozlamalari'

    def __str__(self):
        return 'Bot sozlamalari'

    def save(self, *args, **kwargs):
        # Faqat bitta instance bo'lishini ta'minlash
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


class AdCampaign(models.Model):
    TARGET_AUDIENCE_CHOICES = [
        ('all', 'Hammasi'),
        ('premium', 'Premium'),
        ('free', 'Bepul'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Qoralama'),
        ('scheduled', 'Rejalashtirilgan'),
        ('sending', 'Yuborilmoqda'),
        ('sent', 'Yuborildi'),
        ('failed', 'Xatolik'),
    ]

    name = models.CharField(max_length=255, verbose_name='Kampaniya nomi')
    message = models.TextField(verbose_name='Xabar matni')
    photo = models.ImageField(upload_to='campaigns/', blank=True, null=True, verbose_name='Rasm')
    button_text = models.CharField(max_length=100, blank=True, verbose_name='Tugma matni')
    button_url = models.URLField(blank=True, verbose_name='Tugma havolasi')
    target_audience = models.CharField(max_length=10, choices=TARGET_AUDIENCE_CHOICES, default='all', verbose_name='Maqsadli auditoriya')
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='Rejalashtirish vaqti')
    is_active = models.BooleanField(default=True, verbose_name='Faolmi')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reklama kampaniyasi'
        verbose_name_plural = 'Reklama kampaniyalari'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class PremiumPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField(verbose_name='Muddat (kun)')
    daily_download_limit = models.PositiveIntegerField(default=100)
    daily_shazam_limit = models.PositiveIntegerField(default=50)
    max_file_size_mb = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Premium reja'
        verbose_name_plural = 'Premium rejalar'

    def __str__(self):
        return self.name


class ReferralStats(models.Model):
    referrer = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='referrals_made')
    referred_user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='referred_by_user')
    created_at = models.DateTimeField(auto_now_add=True)
    is_rewarded = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Referal statistikasi'
        verbose_name_plural = 'Referal statistikalari'
        unique_together = [('referrer', 'referred_user')]

    def __str__(self):
        return f'{self.referrer} -> {self.referred_user}'


class ErrorLog(models.Model):
    ERROR_TYPE_CHOICES = [
        ('api_error', 'API xatolik'),
        ('download_error', 'Yuklash xatoligi'),
        ('shazam_error', 'Shazam xatoligi'),
        ('webhook_error', 'Webhook xatoligi'),
        ('system_error', 'Tizim xatoligi'),
    ]

    error_type = models.CharField(max_length=20, choices=ERROR_TYPE_CHOICES)
    message = models.TextField()
    traceback = models.TextField(blank=True)
    user = models.ForeignKey(TelegramUser, null=True, blank=True, on_delete=models.SET_NULL)
    url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Xatolik logi'
        verbose_name_plural = 'Xatolik loglari'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_error_type_display()} - {self.created_at}'
