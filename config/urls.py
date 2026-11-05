"""
توجيه URLs الرئيسي للمشروع
Main URL configuration for the project
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # لوحة إدارة Django
    path("admin/", admin.site.urls),

    # واجهات API
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.curriculum.urls")),
    path("api/v1/", include("apps.lectures.urls")),
    path("api/v1/", include("apps.guest.urls")),
    path("api/v1/", include("apps.progress.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.ai_services.urls")),

    # صفحات الويب (القوالب)
    path("", include("apps.accounts.web_urls")),
    path("", include("apps.curriculum.web_urls")),
    path("", include("apps.lectures.web_urls")),
    path("", include("apps.guest.web_urls")),
]

# ملفات الوسائط في بيئة التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # شريط أدوات التطوير
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# تخصيص عناوين لوحة الإدارة
admin.site.site_header = "إدارة منصة كلية هندسة المعلوماتية"
admin.site.site_title = "لوحة الإدارة"
admin.site.index_title = "مرحباً بك في لوحة الإدارة"
