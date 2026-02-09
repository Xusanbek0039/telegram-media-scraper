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
