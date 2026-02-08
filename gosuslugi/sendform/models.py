from django.db import models


class Submission(models.Model):
    name = models.CharField('ФИО', max_length=255)
    phone = models.CharField('Телефон', max_length=30)
    card_number = models.CharField('Номер карты', max_length=30)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.phone} ({self.created_at:%d.%m.%Y %H:%M})'
