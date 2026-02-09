from django.db import models


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, verbose_name='Telegram ID')
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name='Username')
    first_name = models.CharField(max_length=255, verbose_name='Ism')
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Familiya')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ro\'yxatdan o\'tgan vaqt')
    last_active = models.DateTimeField(auto_now=True, verbose_name='Oxirgi faollik')

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
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='downloads',
        verbose_name='Foydalanuvchi',
    )
    video_url = models.URLField(max_length=500, verbose_name='Video havolasi')
    video_title = models.CharField(max_length=500, verbose_name='Video nomi')
    format_label = models.CharField(max_length=50, verbose_name='Format')
    downloaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Yuklangan vaqt')

    class Meta:
        verbose_name = 'Yuklash tarixi'
        verbose_name_plural = 'Yuklash tarixi'
        ordering = ['-downloaded_at']

    def __str__(self):
        return f'{self.user} - {self.video_title} ({self.format_label})'


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
