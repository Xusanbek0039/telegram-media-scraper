from django.db import models


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, verbose_name='Telegram ID')
    username = models.CharField(max_length=255, null=True, blank=True, verbose_name='Username')
    first_name = models.CharField(max_length=255, verbose_name='Ism')
    last_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='Familiya')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqt')
    last_active = models.DateTimeField(auto_now=True, verbose_name='Oxirgi faollik')

    class Meta:
        verbose_name = 'Telegram foydalanuvchi'
        verbose_name_plural = 'Telegram foydalanuvchilar'
        ordering = ['-last_active']

    def __str__(self):
        return f'{self.first_name} (@{self.username})' if self.username else self.first_name


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
