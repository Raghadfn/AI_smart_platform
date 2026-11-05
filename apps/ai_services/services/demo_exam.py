"""
امتحان NLP عربي عالي الجودة للعرض التوضيحي / الاحتياطي
Curated Arabic NLP MCQ bank for demo / AI-failure fallback
"""
from __future__ import annotations

import re
from typing import Any

# بنك أسئلة أكاديمية جاهزة عن معالجة اللغات الطبيعية
DEMO_NLP_MCQ_BANK: list[dict[str, Any]] = [
    {
        "question": "وفقاً للمفاهيم الأساسية، ماذا تعني معالجة اللغات الطبيعية (NLP)؟",
        "options": [
            "فرع من الذكاء الاصطناعي يهتم بفهم اللغة البشرية ومعالجتها آلياً",
            "تقنية لتصميم شبكات الحاسوب فقط",
            "أسلوب لبرمجة واجهات المستخدم الرسومية",
            "نظام لإدارة قواعد البيانات العلائقية",
        ],
        "correct_answer": "فرع من الذكاء الاصطناعي يهتم بفهم اللغة البشرية ومعالجتها آلياً",
        "explanation": "NLP مجال يمكّن الحاسوب من تحليل اللغة البشرية وفهمها وتوليدها.",
    },
    {
        "question": "أيّ مما يلي يُعدّ مثالاً على مهمة شائعة في معالجة اللغات الطبيعية؟",
        "options": [
            "تحليل المشاعر في النصوص",
            "رسم الدارات الإلكترونية",
            "ضغط ملفات الفيديو",
            "إدارة الذاكرة العشوائية",
        ],
        "correct_answer": "تحليل المشاعر في النصوص",
        "explanation": "تحليل المشاعر من التطبيقات الكلاسيكية لـ NLP على النصوص.",
    },
    {
        "question": "ما الهدف الأساسي من عملية التقطيع (Tokenization) في NLP؟",
        "options": [
            "تقسيم النص إلى وحدات أصغر مثل الكلمات أو الرموز",
            "ترجمة النص إلى لغة برمجة",
            "حذف نظام التشغيل من الذاكرة",
            "تشفير الملفات لحماية الشبكة",
        ],
        "correct_answer": "تقسيم النص إلى وحدات أصغر مثل الكلمات أو الرموز",
        "explanation": "التقطيع يحوّل النص الخام إلى رموز قابلة للمعالجة اللاحقة.",
    },
    {
        "question": "ماذا يقصد بإزالة كلمات التوقف (Stop Words)؟",
        "options": [
            "حذف الكلمات الشائعة قليلة المعنى مثل: في، على، the",
            "حذف جميع الأفعال من الجملة",
            "إزالة علامات الترقيم فقط دون الكلمات",
            "استبدال الأسماء بأرقام عشوائية",
        ],
        "correct_answer": "حذف الكلمات الشائعة قليلة المعنى مثل: في، على، the",
        "explanation": "كلمات التوقف شائعة ولا تضيف غالباً دلالة مهمة للتحليل.",
    },
    {
        "question": "أيّ تقنية تُستخدم لتمثيل الكلمات كمتجهات رقمية تعكس معناها؟",
        "options": [
            "تضمين الكلمات (Word Embeddings)",
            "جدولة المعالجات (CPU Scheduling)",
            "توجيه الحزم الشبكية (Packet Routing)",
            "ضغط الصور بدون فقدان",
        ],
        "correct_answer": "تضمين الكلمات (Word Embeddings)",
        "explanation": "Word Embeddings تمثّل الكلمات في فضاء متجهي يحفظ العلاقات الدلالية.",
    },
    {
        "question": "ما الفرق الجوهري بين stemming و lemmatization؟",
        "options": [
            "lemmatization تُرجع الجذر اللغوي الصحيح، بينما stemming قد يقطع لاحقة بشكل تقريبي",
            "لا يوجد أي فرق بينهما في الاستخدام",
            "stemming يعمل فقط على الصور وlemmatization على الصوت",
            "كلاهما يُستخدمان حصراً في أمن الشبكات",
        ],
        "correct_answer": "lemmatization تُرجع الجذر اللغوي الصحيح، بينما stemming قد يقطع لاحقة بشكل تقريبي",
        "explanation": "التذييل التقريبي (stemming) أبسط، أما الـ lemmatization أدق لغوياً.",
    },
    {
        "question": "أيّ نموذج يُعدّ مناسباً لتصنيف النصوص إلى فئات محددة؟",
        "options": [
            "مصنّف تعلّم آلي مدرَّب على أمثلة نصية مُوسومة",
            "بروتوكول HTTP فقط",
            "خوارزمية فرز سريع للمصفوفات",
            "مولد أرقام عشوائية بدون تدريب",
        ],
        "correct_answer": "مصنّف تعلّم آلي مدرَّب على أمثلة نصية مُوسومة",
        "explanation": "تصنيف النصوص يعتمد عادة على نماذج تعلّم موجَّه ببيانات موسومة.",
    },
    {
        "question": "ما المقصود بـ Named Entity Recognition (NER)؟",
        "options": [
            "التعرّف على كيانات مثل الأسماء والأماكن والتواريخ داخل النص",
            "ضغط الملفات النصية لتوفير المساحة",
            "رسم مخططات UML للبرمجيات",
            "قياس سرعة المعالج أثناء التشغيل",
        ],
        "correct_answer": "التعرّف على كيانات مثل الأسماء والأماكن والتواريخ داخل النص",
        "explanation": "NER يستخرج الكيانات المسماة من النص تلقائياً.",
    },
    {
        "question": "لماذا يُعدّ غموض اللغة (Ambiguity) تحدياً في NLP؟",
        "options": [
            "لأن الكلمة أو الجملة قد تحتمل أكثر من معنى حسب السياق",
            "لأن الحواسيب لا تستطيع تخزين النصوص",
            "لأن الشبكات لا تدعم نقل البيانات النصية",
            "لأن أنظمة التشغيل تمنع قراءة الملفات",
        ],
        "correct_answer": "لأن الكلمة أو الجملة قد تحتمل أكثر من معنى حسب السياق",
        "explanation": "الغموض اللغوي يتطلّب نماذج تفهم السياق لاختيار المعنى الصحيح.",
    },
    {
        "question": "أيّ مما يلي يصف مهمة الترجمة الآلية بشكل صحيح؟",
        "options": [
            "تحويل نص من لغة طبيعية إلى لغة طبيعية أخرى مع الحفاظ على المعنى",
            "تحويل صورة إلى ملف PDF فقط",
            "ترجمة تعليمات المعالج إلى لغة التجميع حصراً",
            "نسخ الملفات بين مجلدات النظام",
        ],
        "correct_answer": "تحويل نص من لغة طبيعية إلى لغة طبيعية أخرى مع الحفاظ على المعنى",
        "explanation": "الترجمة الآلية تنقل المعنى بين اللغات البشرية.",
    },
]


def _norm_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def is_low_quality_exam_questions(questions: list[Any] | None) -> bool:
    """
    True when AI output is unsafe for demo: empty, duplicates, tiny garbage (e.g. SS).
    """
    if not isinstance(questions, list) or not questions:
        return True

    garbage = re.compile(r"^(?:ss+|xx+|aa+|bb+|cc+|dd+|[a-z]{1,2}|\d{1,2}|[أ-ي]{1})$", re.I)

    for item in questions:
        if not isinstance(item, dict):
            return True
        stem = str(item.get("question") or item.get("question_text") or "").strip()
        if len(stem) < 12:
            return True
        options = item.get("options")
        if not isinstance(options, list) or len(options) != 4:
            return True
        cleaned = [str(o).strip() for o in options]
        if any(len(o) < 3 or garbage.match(o) for o in cleaned):
            return True
        keys = [_norm_key(o) for o in cleaned]
        if len(set(keys)) != 4:
            return True
        correct = str(item.get("correct_answer") or "").strip()
        if _norm_key(correct) not in keys:
            return True
    return False


def build_demo_nlp_exam(count: int = 5, title: str = "") -> dict[str, Any]:
    """
    بناء امتحان NLP عربي جاهز بنفس شكل استجابة الواجهة.
    """
    n = max(1, min(int(count or 5), len(DEMO_NLP_MCQ_BANK)))
    selected = DEMO_NLP_MCQ_BANK[:n]
    questions: list[dict[str, Any]] = []
    for i, item in enumerate(selected, start=1):
        questions.append({
            "id": i,
            "type": "mcq",
            "question": item["question"],
            "question_text": item["question"],
            "options": list(item["options"]),
            "correct_answer": item["correct_answer"],
            "explanation": item.get("explanation") or "",
            "source_span": "NLP demo bank",
            "points": 2,
            "difficulty": "medium",
        })

    exam_title = (title or "").strip() or "امتحان تفاعلي — معالجة اللغات الطبيعية"
    if "NLP" not in exam_title and "لغات" not in exam_title:
        exam_title = f"أسئلة امتحان - {exam_title}" if exam_title else exam_title

    return {
        "exam_title": exam_title if exam_title else "امتحان معالجة اللغات الطبيعية",
        "total_questions": len(questions),
        "questions": questions,
        "types": ["mcq"],
        "demo_fallback": True,
        "grounded": True,
        "fallback": True,
    }
