# منصة كلية هندسة المعلوماتية التعليمية

منصة تعليمية مدعومة بالذكاء الاصطناعي لطلاب كلية هندسة المعلوماتية.

## التقنيات المستخدمة

- **Backend:** Django 5 + Django REST Framework
- **Database:** PostgreSQL + pgvector
- **AI:** OpenAI GPT-4
- **Auth:** JWT (djangorestframework-simplejwt)
- **Frontend:** HTML Templates + Tailwind CSS (RTL Arabic)
- **Tasks:** Celery + Redis

## إعداد بيئة التطوير

### 1. إنشاء البيئة الافتراضية وتثبيت المتطلبات

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. إعداد متغيرات البيئة

```bash
copy .env.example .env
# عدّل القيم في ملف .env
```

### 3. تشغيل قاعدة البيانات (PostgreSQL + Redis)

**الخيار أ: Docker (موصى به)**
```bash
docker compose up -d
```

**الخيار ب: Windows بدون Docker**
```powershell
.\scripts\setup_postgresql_windows.ps1
```

ثم عيّن `USE_SQLITE=false` في `.env` لاستخدام PostgreSQL.

### 4. إعداد قاعدة البيانات والهجرات

```bash
python manage.py migrate
python manage.py setup_database      # تفعيل pgvector, pg_trgm, unaccent
python manage.py check_database      # فحص الاتصال والامتدادات
python manage.py seed_curriculum     # بذر السنوات والمواد الدراسية
python manage.py createsuperuser
```

### 5. تشغيل الخادم

```bash
python manage.py runserver
```

افتح: http://127.0.0.1:8000/

## هيكل المشروع

```
informatics_platform/
├── config/           # إعدادات Django
├── apps/             # التطبيقات
│   ├── accounts/     # المصادقة والمستخدمون
│   ├── curriculum/   # السنوات والمواد
│   ├── lectures/     # المحاضرات
│   ├── ai_services/  # خدمات الذكاء الاصطناعي
│   ├── guest/        # وضع الزائر
│   ├── progress/     # تتبع التقدم
│   └── notifications/# الإشعارات
├── templates/        # قوالب HTML
├── static/           # ملفات ثابتة
└── media/            # ملفات مرفوعة
```

## مراحل التطوير

- [x] الخطوة 1: إعداد المشروع
- [x] الخطوة 2: إعداد قاعدة البيانات
- [x] الخطوة 3: نظام المصادقة
- [x] الخطوة 5: الواجهات والقوالب
- [x] الخطوة 6: تكامل الذكاء الاصطناعي
- [ ] الخطوة 7: وضع الزائر
- [ ] الخطوة 8: الميزات المتقدمة
- [ ] الخطوة 9: تحسين الواجهة
- [ ] الخطوة 10: الاختبار والنشر
