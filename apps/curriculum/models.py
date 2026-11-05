"""
نماذج المنهج الدراسي - السنوات والفصول والاختصاصات والمواد
Curriculum models - years, semesters, specializations, subjects
"""
import uuid

from django.db import models


class AcademicYear(models.Model):
    """السنة الأكاديمية (الأولى إلى الخامسة)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_ar = models.CharField(max_length=100, verbose_name="الاسم بالعربية")
    name_en = models.CharField(max_length=100, verbose_name="الاسم بالإنجليزية")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="الرابط")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "سنة أكاديمية"
        verbose_name_plural = "السنوات الأكاديمية"
        ordering = ["order"]

    @property
    def has_specializations(self):
        return self.order >= 4

    def __str__(self):
        return self.name_ar


class Semester(models.Model):
    """الفصل الدراسي (الأول أو الثاني) ضمن سنة أكاديمية"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="semesters",
        verbose_name="السنة الأكاديمية",
    )
    number = models.PositiveSmallIntegerField(verbose_name="رقم الفصل")
    name_ar = models.CharField(max_length=100, verbose_name="الاسم بالعربية")
    name_en = models.CharField(max_length=100, verbose_name="الاسم بالإنجليزية")
    slug = models.SlugField(max_length=80, unique=True, verbose_name="الرابط")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "فصل دراسي"
        verbose_name_plural = "الفصول الدراسية"
        ordering = ["year__order", "number"]
        unique_together = [["year", "number"]]

    def __str__(self):
        return f"{self.year.name_ar} - {self.name_ar}"


class Specialization(models.Model):
    """اختصاص أكاديمي (السنة الرابعة والخامسة فقط)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="specializations",
        verbose_name="السنة الأكاديمية",
    )
    name_ar = models.CharField(max_length=150, verbose_name="الاسم بالعربية")
    name_en = models.CharField(max_length=150, verbose_name="الاسم بالإنجليزية")
    slug = models.SlugField(max_length=80, verbose_name="الرابط")
    description_ar = models.TextField(blank=True, verbose_name="الوصف")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "اختصاص"
        verbose_name_plural = "الاختصاصات"
        ordering = ["year__order", "order"]
        unique_together = [["year", "slug"]]

    def __str__(self):
        return f"{self.year.name_ar} - {self.name_ar}"


class Subject(models.Model):
    """المادة الدراسية"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name="subjects",
        verbose_name="الفصل الدراسي",
    )
    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subjects",
        verbose_name="الاختصاص",
    )
    name_ar = models.CharField(max_length=200, verbose_name="الاسم بالعربية")
    name_en = models.CharField(max_length=200, verbose_name="الاسم بالإنجليزية")
    slug = models.SlugField(max_length=120, verbose_name="الرابط")
    description_ar = models.TextField(blank=True, verbose_name="الوصف")
    icon = models.CharField(max_length=50, blank=True, verbose_name="أيقونة")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "مادة دراسية"
        verbose_name_plural = "المواد الدراسية"
        ordering = ["semester__year__order", "semester__number", "specialization__order", "order"]
        unique_together = [["semester", "slug"]]

    @property
    def year(self):
        return self.semester.year

    def __str__(self):
        if self.specialization:
            return f"{self.specialization.name_ar} - {self.name_ar}"
        return f"{self.semester.year.name_ar} - {self.name_ar}"
