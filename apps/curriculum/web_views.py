"""
واجهات صفحات المنهج الدراسي
Curriculum web template views
"""
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.views.generic import DetailView, TemplateView

from apps.accounts.mixins import StudentRequiredMixin
from apps.lectures.models import Lecture

from .models import AcademicYear, Semester, Specialization, Subject


def _published_lectures_prefetch() -> Prefetch:
    """Prefetch published lectures only (matches subject/detail pages)."""
    return Prefetch(
        "lectures",
        queryset=Lecture.objects.filter(is_published=True).order_by("order"),
        to_attr="published_lectures",
    )


class YearSubjectsView(StudentRequiredMixin, DetailView):
    """
    عرض المواد الدراسية لسنة أكاديمية
    السنوات 1-3: مجمّعة حسب الفصل
    السنوات 4-5: مجمّعة حسب الاختصاص ثم الفصل
    GET /year/<slug>/
    """

    model = AcademicYear
    slug_url_kwarg = "year_slug"
    context_object_name = "year"
    template_name = "dashboard/year.html"

    def get_queryset(self):
        return AcademicYear.objects.filter(is_active=True).prefetch_related(
            Prefetch(
                "semesters",
                queryset=Semester.objects.filter(is_active=True).order_by("number"),
            ),
            Prefetch(
                "specializations",
                queryset=Specialization.objects.filter(is_active=True).order_by("order"),
            ),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.object
        semesters = list(year.semesters.all())
        has_specializations = year.order >= 4
        published_prefetch = _published_lectures_prefetch()

        context["has_specializations"] = has_specializations
        context["semesters"] = semesters

        if has_specializations:
            specializations = list(year.specializations.all())
            context["specializations"] = specializations
            context["subject_count"] = Subject.objects.filter(
                semester__year=year, is_active=True
            ).count()

            active_track = self.request.GET.get("track", specializations[0].slug if specializations else "")
            context["active_track"] = active_track

            track_data = []
            for spec in specializations:
                sem_sections = []
                for sem in semesters:
                    subjects = list(
                        Subject.objects.filter(
                            semester=sem, specialization=spec, is_active=True
                        )
                        .annotate(
                            published_lecture_count=Count(
                                "lectures",
                                filter=Q(lectures__is_published=True),
                            )
                        )
                        .prefetch_related(published_prefetch)
                        .order_by("order")
                    )
                    sem_sections.append({"semester": sem, "subjects": subjects})
                track_data.append({
                    "specialization": spec,
                    "semesters": sem_sections,
                    "is_active": spec.slug == active_track,
                })
            context["track_data"] = track_data
        else:
            for sem in semesters:
                sem.prefetched_subjects = list(
                    Subject.objects.filter(
                        semester=sem, specialization__isnull=True, is_active=True
                    )
                    .annotate(
                        published_lecture_count=Count(
                            "lectures",
                            filter=Q(lectures__is_published=True),
                        )
                    )
                    .prefetch_related(published_prefetch)
                    .order_by("order")
                )
            context["subject_count"] = sum(len(s.prefetched_subjects) for s in semesters)

        context["breadcrumb"] = [
            {"label": "لوحة التحكم", "url": "/dashboard/"},
            {"label": year.name_ar, "url": None},
        ]
        return context


class SubjectLecturesView(StudentRequiredMixin, DetailView):
    """عرض محاضرات مادة دراسية"""

    model = Subject
    context_object_name = "subject"
    template_name = "dashboard/subject.html"

    def get_object(self, queryset=None):
        year_slug = self.kwargs.get("year_slug")
        subject_slug = self.kwargs.get("subject_slug")

        try:
            return (
                Subject.objects.select_related(
                    "semester", "semester__year", "specialization"
                )
                .prefetch_related(_published_lectures_prefetch())
                .get(
                    semester__year__slug=year_slug,
                    semester__year__is_active=True,
                    slug=subject_slug,
                    is_active=True,
                )
            )
        except Subject.DoesNotExist as exc:
            raise Http404("المادة الدراسية غير موجودة.") from exc
        except Subject.MultipleObjectsReturned:
            # Same slug in two semesters of one year — pick the first active match
            subject = (
                Subject.objects.select_related(
                    "semester", "semester__year", "specialization"
                )
                .prefetch_related(_published_lectures_prefetch())
                .filter(
                    semester__year__slug=year_slug,
                    semester__year__is_active=True,
                    slug=subject_slug,
                    is_active=True,
                )
                .order_by("semester__number", "order")
                .first()
            )
            if subject is None:
                raise Http404("المادة الدراسية غير موجودة.")
            return subject

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if hasattr(self.object, "published_lectures"):
            lectures = self.object.published_lectures
        else:
            lectures = list(
                self.object.lectures.filter(is_published=True).order_by("order")
            )

        progress_map = {}
        if user.is_authenticated:
            from apps.progress.models import LectureProgress

            progress_qs = LectureProgress.objects.filter(user=user, lecture__in=lectures)
            progress_map = {p.lecture_id: p for p in progress_qs}

        context["lectures_data"] = [
            {
                "lecture": lecture,
                "progress": progress_map.get(lecture.id),
                "progress_percent": progress_map[lecture.id].progress_percent if lecture.id in progress_map else 0,
                "status": progress_map[lecture.id].status if lecture.id in progress_map else "not_started",
            }
            for lecture in lectures
        ]

        breadcrumb = [
            {"label": "لوحة التحكم", "url": "/dashboard/"},
            {"label": self.object.year.name_ar, "url": f"/year/{self.object.year.slug}/"},
        ]
        if self.object.specialization:
            breadcrumb.append({
                "label": self.object.specialization.name_ar,
                "url": f"/year/{self.object.year.slug}/?track={self.object.specialization.slug}",
            })
        breadcrumb.append({"label": self.object.name_ar, "url": None})
        context["breadcrumb"] = breadcrumb
        return context


class SearchView(StudentRequiredMixin, TemplateView):
    """البحث في المحاضرات"""

    template_name = "dashboard/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        context["query"] = query

        if query:
            context["lectures"] = (
                Lecture.objects.filter(is_published=True)
                .filter(
                    Q(title_ar__icontains=query)
                    | Q(title_en__icontains=query)
                    | Q(content_text__icontains=query)
                    | Q(subject__name_ar__icontains=query)
                )
                .select_related(
                    "subject", "subject__semester", "subject__semester__year", "subject__specialization"
                )
                .order_by("subject__semester__year__order", "order")[:30]
            )
        else:
            context["lectures"] = []

        return context
