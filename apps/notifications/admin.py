from django.contrib import admin

from .models import Notification, NotificationRead


class NotificationReadInline(admin.TabularInline):
    model = NotificationRead
    extra = 0
    readonly_fields = ("user", "read_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title_ar", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title_ar", "message_ar")
    inlines = [NotificationReadInline]


@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ("notification", "user", "read_at")
    list_filter = ("read_at",)
