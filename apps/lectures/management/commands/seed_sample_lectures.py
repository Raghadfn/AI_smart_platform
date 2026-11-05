"""
أمر بذر محاضرات تجريبية للاختبار
Management command: seed_sample_lectures
"""
from django.core.management.base import BaseCommand

from apps.curriculum.models import Subject
from apps.lectures.models import Lecture


SAMPLE_LECTURES = {
    "python-programming": [
        {
            "title_ar": "مقدمة في البرمجة",
            "title_en": "Introduction to Programming",
            "slug": "intro-programming",
            "order": 1,
            "duration_minutes": 15,
            "content_text": """# مقدمة في البرمجة

## ما هي البرمجة؟
البرمجة هي عملية كتابة تعليمات للحاسوب لتنفيذ مهام محددة. تُستخدم لغات البرمجة كوسيط بين الم programmer والحاسوب.

## لماذا بايثون؟
- سهلة التعلم للمبتدئين
- مفتوحة المصدر ومجانية
- تستخدم في الذكاء الاصطناعي وتحليل البيانات
- مجتمع كبير ودعم واسع

## أول برنامج
```python
print("مرحباً بالعالم!")
```

## المتغيرات
المتغير هو مكان في الذاكرة لتخزين البيانات:
```python
name = "أحمد"
age = 20
print(f"الاسم: {name}, العمر: {age}")
```
""",
        },
        {
            "title_ar": "الشروط والحلقات",
            "title_en": "Conditions and Loops",
            "slug": "conditions-loops",
            "order": 2,
            "duration_minutes": 20,
            "content_text": """# الشروط والحلقات في بايثون

## جملة if
```python
score = 85
if score >= 90:
    print("ممتاز")
elif score >= 75:
    print("جيد جداً")
else:
    print("جيد")
```

## حلقة for
```python
for i in range(5):
    print(i)
```

## حلقة while
```python
count = 0
while count < 3:
    print(count)
    count += 1
```
""",
        },
    ],
    "data-structures": [
        {
            "title_ar": "المصفوفات والقوائم",
            "title_en": "Arrays and Lists",
            "slug": "arrays-lists",
            "order": 1,
            "duration_minutes": 25,
            "content_text": """# المصفوفات والقوائم

## القائمة (List)
بنية بيانات لتخزين عناصر متعددة:
```python
numbers = [1, 2, 3, 4, 5]
fruits = ["تفاح", "موز", "برتقال"]
```

## العمليات الأساسية
- الإضافة: append(), insert()
- الحذف: remove(), pop()
- البحث: index(), in
- الترتيب: sort(), reverse()

## التعقيد الزمني
- الوصول: O(1)
- البحث: O(n)
- الإدراج: O(n)
""",
        },
    ],
    "machine-learning": [
        {
            "title_ar": "مقدمة في تعلم الآلة",
            "title_en": "Introduction to Machine Learning",
            "slug": "intro-ml",
            "order": 1,
            "duration_minutes": 30,
            "content_text": """# مقدمة في تعلم الآلة

## ما هو تعلم الآلة؟
تعلم الآلة (ML) فرع من الذكاء الاصطناعي يمكّن الحواسيب من التعلم من البيانات دون برمجة صريحة لكل قاعدة.

## أنواع التعلم
1. **التعلم المُشرف**: تدريب على بيانات مُصنّفة
2. **التعلم غير المُشرف**: اكتشاف أنماط بدون تصنيفات
3. **التعلم المعزز**: التعلم بالمكافآت

## التطبيقات
- التصنيف والتنبؤ
- التجميع واكتشاف الشذوذ
- أنظمة التوصية
""",
        },
    ],
}


class Command(BaseCommand):
    help = "بذر محاضرات تجريبية للاختبار"

    def handle(self, *args, **options):
        created_count = 0

        for subject_slug, lectures in SAMPLE_LECTURES.items():
            subjects = Subject.objects.filter(slug=subject_slug, is_active=True)
            if not subjects.exists():
                self.stdout.write(self.style.WARNING(f"  تخطي: المادة '{subject_slug}' غير موجودة"))
                continue

            for subject in subjects:
                for lec_data in lectures:
                    lecture, created = Lecture.objects.get_or_create(
                        subject=subject,
                        slug=lec_data["slug"],
                        defaults={
                            **lec_data,
                            "is_published": True,
                            "processing_status": Lecture.ProcessingStatus.READY,
                        },
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  + {subject.semester.year.name_ar} / {subject.name_ar}: {lecture.title_ar}"
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS(f"\nاكتمل: {created_count} محاضرة جديدة")
        )
