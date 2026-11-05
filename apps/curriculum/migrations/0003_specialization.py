# Specialization tracks for years 4 and 5

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("curriculum", "0002_semester_structure"),
    ]

    operations = [
        migrations.CreateModel(
            name="Specialization",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name_ar", models.CharField(max_length=150, verbose_name="الاسم بالعربية")),
                ("name_en", models.CharField(max_length=150, verbose_name="الاسم بالإنجليزية")),
                ("slug", models.SlugField(max_length=80, verbose_name="الرابط")),
                ("description_ar", models.TextField(blank=True, verbose_name="الوصف")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="الترتيب")),
                ("is_active", models.BooleanField(default=True, verbose_name="نشط")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")),
                (
                    "year",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="specializations",
                        to="curriculum.academicyear",
                        verbose_name="السنة الأكاديمية",
                    ),
                ),
            ],
            options={
                "verbose_name": "اختصاص",
                "verbose_name_plural": "الاختصاصات",
                "ordering": ["year__order", "order"],
                "unique_together": {("year", "slug")},
            },
        ),
        migrations.AddField(
            model_name="subject",
            name="specialization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subjects",
                to="curriculum.specialization",
                verbose_name="الاختصاص",
            ),
        ),
        migrations.AlterField(
            model_name="subject",
            name="slug",
            field=models.SlugField(max_length=120, verbose_name="الرابط"),
        ),
        migrations.AlterModelOptions(
            name="subject",
            options={
                "ordering": ["semester__year__order", "semester__number", "specialization__order", "order"],
                "verbose_name": "مادة دراسية",
                "verbose_name_plural": "المواد الدراسية",
            },
        ),
    ]
