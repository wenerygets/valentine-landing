from django.contrib import admin
from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'card_number', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'phone', 'card_number')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
