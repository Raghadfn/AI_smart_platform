# Generated manually for 5-year semester structure

import django.db.models.deletion
import uuid
from django.db import migrations, models


def clear_old_curriculum(apps, schema_editor):
    """حذف بيانات المنهج القديم قبل إعادة الهيكلة"""
    Subject = apps.get_model("curriculum", "Subject")
    Subject.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("curriculum", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Semester",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("number", models.PositiveSmallIntegerField(verbose_name="رقم الفصل")),
                ("name_ar", models.CharField(max_length=100, verbose_name="الاسم بالعربية")),
                ("name_en", models.CharField(max_length=100, verbose_name="الاسم بالإنجليزية")),
                ("slug", models.SlugField(max_length=80, unique=True, verbose_name="الرابط")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="الترتيب")),
                ("is_active", models.BooleanField(default=True, verbose_name="نشط")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")),
                (
                    "year",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="semesters",
                        to="curriculum.academicyear",
                        verbose_name="السنة الأكاديمية",
                    ),
                ),
            ],
            options={
                "verbose_name": "فصل دراسي",
                "verbose_name_plural": "الفصول الدراسية",
                "ordering": ["year__order", "number"],
                "unique_together": {("year", "number")},
            },
        ),
        migrations.RunPython(clear_old_curriculum, migrations.RunPython.noop),
        migrations.AddField(
            model_name="subject",
            name="semester",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subjects",
                to="curriculum.semester",
                verbose_name="الفصل الدراسي",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="subject",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="subject",
            name="year",
        ),
        migrations.AlterField(
            model_name="subject",
            name="semester",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subjects",
                to="curriculum.semester",
                verbose_name="الفصل الدراسي",
            ),
        ),
        migrations.AlterModelOptions(
            name="subject",
            options={
                "ordering": ["semester__year__order", "semester__number", "order"],
                "verbose_name": "مادة دراسية",
                "verbose_name_plural": "المواد الدراسية",
            },
        ),
        migrations.AlterUniqueTogether(
            name="subject",
            unique_together={("semester", "slug")},
        ),
    ]
