"""
أمر بذر البيانات الأولية للمنهج الدراسي
Management command: seed_curriculum — 5 years with specializations for years 4-5
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.curriculum.curriculum_data import (
    CURRICULUM_DATA,
    SPECIALIZATION_DEFINITIONS,
    SPECIALIZED_SUBJECTS,
)
from apps.curriculum.models import AcademicYear, Semester, Specialization, Subject


class Command(BaseCommand):
    help = "بذر المنهج: 5 سنوات، اختصاصات للسنة 4-5، 6 مواد/فصل للسنوات 1-3"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="حذف البيانات الموجودة قبل البذر")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("حذف بيانات المنهج القديمة..."))
            AcademicYear.objects.all().delete()

        stats = {"years": 0, "semesters": 0, "specializations": 0, "subjects": 0}

        for item in CURRICULUM_DATA:
            year = self._seed_year(item, stats)
            if item.get("has_specializations"):
                self._seed_specialized_year(year, item, stats)
            else:
                self._seed_general_year(year, item, stats)

        self._print_summary(stats)
        self._validate_distribution()

    def _seed_year(self, item, stats):
        year_data = item["year"]
        year, created = AcademicYear.objects.get_or_create(slug=year_data["slug"], defaults=year_data)
        if not created:
            for field, value in year_data.items():
                setattr(year, field, value)
            year.save()
        else:
            stats["years"] += 1
            self.stdout.write(self.style.SUCCESS(f"  + سنة: {year.name_ar}"))
        return year

    def _seed_general_year(self, year, item, stats):
        for sem_data in item["semesters"]:
            semester = self._get_or_create_semester(year, sem_data, stats)
            subjects = sem_data["subjects"]
            self.stdout.write(f"    مواد {semester.name_ar}: {len(subjects)}")
            for subj_data in subjects:
                self._get_or_create_subject(semester, subj_data, specialization=None, stats=stats)

    def _seed_specialized_year(self, year, item, stats):
        semester_map = {}
        for sem_data in item["semesters"]:
            semester = self._get_or_create_semester(year, sem_data, stats)
            semester_map[sem_data["number"]] = semester

        year_slug = year.slug
        track_subjects = SPECIALIZED_SUBJECTS.get(year_slug, {})

        for spec_def in SPECIALIZATION_DEFINITIONS:
            spec, spec_created = Specialization.objects.get_or_create(
                year=year,
                slug=spec_def["slug"],
                defaults={
                    "name_ar": spec_def["name_ar"],
                    "name_en": spec_def["name_en"],
                    "order": spec_def["order"],
                    "description_ar": spec_def.get("description_ar", ""),
                },
            )
            if not spec_created:
                for field in ("name_ar", "name_en", "order", "description_ar"):
                    setattr(spec, field, spec_def.get(field, getattr(spec, field)))
                spec.save()
            else:
                stats["specializations"] += 1
                self.stdout.write(self.style.SUCCESS(f"    + اختصاص: {spec.name_ar}"))

            spec_subjects = track_subjects.get(spec_def["slug"], {})
            for sem_number, semester in semester_map.items():
                subjects = spec_subjects.get(sem_number, [])
                self.stdout.write(f"      {spec.name_ar} / {semester.name_ar}: {len(subjects)} مواد")
                for subj_data in subjects:
                    self._get_or_create_subject(semester, subj_data, specialization=spec, stats=stats)

    def _get_or_create_semester(self, year, sem_data, stats):
        defaults = {
            "number": sem_data["number"],
            "name_ar": sem_data["name_ar"],
            "name_en": sem_data["name_en"],
            "order": sem_data["number"],
            "year": year,
        }
        semester, created = Semester.objects.get_or_create(slug=sem_data["slug"], defaults=defaults)
        if not created:
            for field, value in defaults.items():
                setattr(semester, field, value)
            semester.save()
        else:
            stats["semesters"] += 1
            self.stdout.write(f"    + فصل: {semester.name_ar}")
        return semester

    def _get_or_create_subject(self, semester, subj_data, specialization, stats):
        defaults = {**subj_data, "specialization": specialization}
        subject, created = Subject.objects.get_or_create(
            semester=semester,
            slug=subj_data["slug"],
            defaults=defaults,
        )
        if not created:
            for field, value in defaults.items():
                setattr(subject, field, value)
            subject.save()
        else:
            stats["subjects"] += 1
            prefix = f"        + [{specialization.name_ar}] " if specialization else "        + "
            self.stdout.write(f"{prefix}{subject.name_ar}")

    def _print_summary(self, stats):
        self.stdout.write(self.style.SUCCESS(
            f"\nاكتمل البذر: {stats['years']} سنة، {stats['semesters']} فصل، "
            f"{stats['specializations']} اختصاص، {stats['subjects']} مادة جديدة"
        ))
        self.stdout.write(
            f"الإجمالي: {AcademicYear.objects.count()} سنوات، "
            f"{Semester.objects.count()} فصول، "
            f"{Specialization.objects.count()} اختصاصات، "
            f"{Subject.objects.count()} مواد"
        )

    def _validate_distribution(self):
        errors = []
        general_rules = {1: (6, 6), 2: (6, 6), 3: (6, 6)}
        spec_rules = (5, 4)

        for year in AcademicYear.objects.order_by("order"):
            semesters = list(year.semesters.order_by("number"))
            if len(semesters) != 2:
                errors.append(f"{year.name_ar}: يجب أن تحتوي على فصلين")
                continue

            if year.order <= 3:
                expected = general_rules[year.order]
                counts = [s.subjects.filter(specialization__isnull=True).count() for s in semesters]
                if counts != list(expected):
                    errors.append(f"{year.name_ar}: متوقع {expected}, وُجد {counts}")
            else:
                specs = list(year.specializations.order_by("order"))
                if len(specs) != 3:
                    errors.append(f"{year.name_ar}: يجب أن تحتوي على 3 اختصاصات (وُجد {len(specs)})")
                for spec in specs:
                    counts = [
                        s.subjects.filter(specialization=spec).count()
                        for s in semesters
                    ]
                    if counts != list(spec_rules):
                        errors.append(
                            f"{year.name_ar}/{spec.name_ar}: متوقع 5+4، وُجد {counts[0]}+{counts[1]}"
                        )

        if errors:
            for err in errors:
                self.stdout.write(self.style.ERROR(f"  تحذير: {err}"))
        else:
            self.stdout.write(self.style.SUCCESS("  توزيع المواد والاختصاصات صحيح"))
