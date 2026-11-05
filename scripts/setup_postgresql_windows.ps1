# ============================================
# سكربت تثبيت PostgreSQL على Windows
# PostgreSQL + pgvector installation guide for Windows
# ============================================
#
# الخيار 1: Docker Desktop (موصى به)
# --------------------------------
# 1. ثبّت Docker Desktop من: https://www.docker.com/products/docker-desktop/
# 2. شغّل: docker compose up -d
# 3. عيّن USE_SQLITE=false في ملف .env
#
# الخيار 2: PostgreSQL محلي
# --------------------------------
# 1. حمّل PostgreSQL 16 من: https://www.postgresql.org/download/windows/
# 2. ثبّت مع كلمة مرور للمستخدم postgres
# 3. أنشئ قاعدة البيانات:
#    psql -U postgres -c "CREATE DATABASE informatics_db;"
# 4. ثبّت pgvector:
#    - حمّل من: https://github.com/pgvector/pgvector/releases
#    - أو استخدم: CREATE EXTENSION vector; (بعد تثبيت الامتداد)
# 5. عيّن في .env:
#    USE_SQLITE=false
#    DB_NAME=informatics_db
#    DB_USER=postgres
#    DB_PASSWORD=your_password
#
# الخيار 3: SQLite (تطوير محدود - بدون pgvector)
# --------------------------------
# USE_SQLITE=true في .env
# ملاحظة: ميزات البحث الدلالي (RAG) تتطلب PostgreSQL
#
# ============================================
# أوامر الإعداد بعد تثبيت PostgreSQL
# ============================================
#
# cd d:\newweb
# .\venv\Scripts\Activate.ps1
# python manage.py migrate
# python manage.py setup_database
# python manage.py check_database
# python manage.py seed_curriculum
# python manage.py createsuperuser
#

Write-Host "=== دليل تثبيت PostgreSQL ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "راجع التعليقات في هذا الملف: scripts\setup_postgresql_windows.ps1"
Write-Host ""
Write-Host "للتطوير السريع بدون PostgreSQL، استخدم USE_SQLITE=true في .env"
Write-Host "للميزات الكاملة (pgvector + RAG)، استخدم PostgreSQL مع USE_SQLITE=false"
Write-Host ""

# فحص إذا كان PostgreSQL يعمل على المنفذ 5432
$tcpTest = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
if ($tcpTest.TcpTestSucceeded) {
    Write-Host "[OK] PostgreSQL يعمل على المنفذ 5432" -ForegroundColor Green
} else {
    Write-Host "[--] PostgreSQL غير متاح على المنفذ 5432" -ForegroundColor Yellow
    Write-Host "     استخدم Docker أو ثبّت PostgreSQL يدوياً"
}

# فحص Docker
try {
    $dockerVersion = docker --version 2>$null
    if ($dockerVersion) {
        Write-Host "[OK] Docker متوفر: $dockerVersion" -ForegroundColor Green
        Write-Host "     شغّل: docker compose up -d"
    }
} catch {
    Write-Host "[--] Docker غير مثبت" -ForegroundColor Yellow
}
