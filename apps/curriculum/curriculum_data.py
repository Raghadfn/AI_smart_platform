"""
بيانات المنهج الدراسي - 5 سنوات مع اختصاصات للسنة الرابعة والخامسة
5-year curriculum with specializations for years 4 and 5
"""

# الاختصاصات الثلاثة (تُطبَّق على السنة الرابعة والخامسة)
SPECIALIZATION_DEFINITIONS = [
    {
        "slug": "software-engineering",
        "name_ar": "هندسة البرمجيات",
        "name_en": "Software Engineering",
        "order": 1,
        "description_ar": "تطوير الأنظمة البرمجية، معمارية البرمجيات، DevOps، وضمان الجودة",
    },
    {
        "slug": "artificial-intelligence",
        "name_ar": "الذكاء الاصطناعي",
        "name_en": "Artificial Intelligence",
        "order": 2,
        "description_ar": "تعلم الآلة، التعلم العميق، معالجة اللغات، والرؤية الحاسوبية",
    },
    {
        "slug": "computer-networks",
        "name_ar": "الشبكات الحاسوبية",
        "name_en": "Computer Networks",
        "order": 3,
        "description_ar": "شبكات الحاسوب، الأمن السيبراني، البنية التحتية، والحوسبة السحابية",
    },
]

# ─── السنوات 1-3: منهج عام موحّد (6 مواد لكل فصل) ───

GENERAL_YEARS = [
    {
        "year": {"name_ar": "السنة الأولى", "name_en": "First Year", "slug": "year-1", "order": 1},
        "semesters": [
            {
                "number": 1, "name_ar": "الفصل الأول", "name_en": "Semester 1", "slug": "year-1-sem-1",
                "subjects": [
                    {"name_ar": "الرياضيات التحليلية", "name_en": "Analytical Mathematics", "slug": "analytical-math", "order": 1},
                    {"name_ar": "الفيزياء العامة", "name_en": "General Physics", "slug": "general-physics", "order": 2},
                    {"name_ar": "مقدمة في الحاسوب", "name_en": "Introduction to Computing", "slug": "intro-computing", "order": 3},
                    {"name_ar": "البرمجة بلغة C", "name_en": "C Programming", "slug": "c-programming", "order": 4},
                    {"name_ar": "اللغة الإنجليزية التقنية", "name_en": "Technical English", "slug": "technical-english", "order": 5},
                    {"name_ar": "مهارات الاتصال والتفكير النقدي", "name_en": "Communication & Critical Thinking", "slug": "communication-skills", "order": 6},
                ],
            },
            {
                "number": 2, "name_ar": "الفصل الثاني", "name_en": "Semester 2", "slug": "year-1-sem-2",
                "subjects": [
                    {"name_ar": "الجبر الخطي", "name_en": "Linear Algebra", "slug": "linear-algebra", "order": 1},
                    {"name_ar": "الكهرباء والإلكترونيات الأساسية", "name_en": "Basic Electrical & Electronics", "slug": "basic-electronics", "order": 2},
                    {"name_ar": "البرمجة بلغة بايثون", "name_en": "Python Programming", "slug": "python-programming", "order": 3},
                    {"name_ar": "مبادئ هندسة البرمجيات", "name_en": "Software Engineering Principles", "slug": "se-principles", "order": 4},
                    {"name_ar": "الإحصاء والاحتمالات", "name_en": "Statistics & Probability", "slug": "statistics", "order": 5},
                    {"name_ar": "التصميم المنطقي والدوائر", "name_en": "Logic Design & Circuits", "slug": "logic-design", "order": 6},
                ],
            },
        ],
    },
    {
        "year": {"name_ar": "السنة الثانية", "name_en": "Second Year", "slug": "year-2", "order": 2},
        "semesters": [
            {
                "number": 1, "name_ar": "الفصل الأول", "name_en": "Semester 1", "slug": "year-2-sem-1",
                "subjects": [
                    {"name_ar": "هياكل البيانات", "name_en": "Data Structures", "slug": "data-structures", "order": 1},
                    {"name_ar": "الخوارزميات", "name_en": "Algorithms", "slug": "algorithms", "order": 2},
                    {"name_ar": "البرمجة الكائنية المتقدمة", "name_en": "Advanced OOP", "slug": "advanced-oop", "order": 3},
                    {"name_ar": "قواعد البيانات", "name_en": "Databases", "slug": "databases", "order": 4},
                    {"name_ar": "الشبكات الحاسوبية", "name_en": "Computer Networks", "slug": "networks", "order": 5},
                    {"name_ar": "نظرية الحوسبة", "name_en": "Theory of Computation", "slug": "computation-theory", "order": 6},
                ],
            },
            {
                "number": 2, "name_ar": "الفصل الثاني", "name_en": "Semester 2", "slug": "year-2-sem-2",
                "subjects": [
                    {"name_ar": "أنظمة التشغيل", "name_en": "Operating Systems", "slug": "operating-systems", "order": 1},
                    {"name_ar": "هندسة البرمجيات", "name_en": "Software Engineering", "slug": "software-engineering", "order": 2},
                    {"name_ar": "تطوير تطبيقات الويب", "name_en": "Web Application Development", "slug": "web-development", "order": 3},
                    {"name_ar": "الرياضيات المتقطعة", "name_en": "Discrete Mathematics", "slug": "discrete-math", "order": 4},
                    {"name_ar": "مقدمة في الأمن السيبراني", "name_en": "Introduction to Cybersecurity", "slug": "cybersecurity-intro", "order": 5},
                    {"name_ar": "مقدمة في الذكاء الاصطناعي", "name_en": "Introduction to AI", "slug": "ai-intro", "order": 6},
                ],
            },
        ],
    },
    {
        "year": {"name_ar": "السنة الثالثة", "name_en": "Third Year", "slug": "year-3", "order": 3},
        "semesters": [
            {
                "number": 1, "name_ar": "الفصل الأول", "name_en": "Semester 1", "slug": "year-3-sem-1",
                "subjects": [
                    {"name_ar": "تعلم الآلة", "name_en": "Machine Learning", "slug": "machine-learning", "order": 1},
                    {"name_ar": "معالجة اللغات الطبيعية", "name_en": "Natural Language Processing", "slug": "nlp", "order": 2},
                    {"name_ar": "الرؤية الحاسوبية", "name_en": "Computer Vision", "slug": "computer-vision", "order": 3},
                    {"name_ar": "تحليل وتصميم الخوارزميات المتقدم", "name_en": "Advanced Algorithm Design", "slug": "advanced-algorithms", "order": 4},
                    {"name_ar": "هندسة البيانات", "name_en": "Data Engineering", "slug": "data-engineering", "order": 5},
                    {"name_ar": "الأنظمة الموزعة", "name_en": "Distributed Systems", "slug": "distributed-systems", "order": 6},
                ],
            },
            {
                "number": 2, "name_ar": "الفصل الثاني", "name_en": "Semester 2", "slug": "year-3-sem-2",
                "subjects": [
                    {"name_ar": "التعلم العميق", "name_en": "Deep Learning", "slug": "deep-learning", "order": 1},
                    {"name_ar": "البيانات الضخمة", "name_en": "Big Data", "slug": "big-data", "order": 2},
                    {"name_ar": "الحوسبة السحابية", "name_en": "Cloud Computing", "slug": "cloud-computing", "order": 3},
                    {"name_ar": "إنترنت الأشياء", "name_en": "Internet of Things", "slug": "iot", "order": 4},
                    {"name_ar": "هندسة أمن المعلومات", "name_en": "Information Security Engineering", "slug": "security-engineering", "order": 5},
                    {"name_ar": "نمذجة ومحاكاة الأنظمة", "name_en": "Systems Modeling & Simulation", "slug": "systems-simulation", "order": 6},
                ],
            },
        ],
    },
]

# ─── مواد الاختصاصات للسنة الرابعة والخامسة (5+4 لكل اختصاص) ───

SPECIALIZED_SUBJECTS = {
    "year-4": {
        "software-engineering": {
            1: [
                {"name_ar": "معمارية البرمجيات المتقدمة", "name_en": "Advanced Software Architecture", "slug": "y4-se-sw-architecture", "order": 1},
                {"name_ar": "DevOps وهندسة النشر", "name_en": "DevOps Engineering", "slug": "y4-se-devops", "order": 2},
                {"name_ar": "اختبار البرمجيات وضمان الجودة", "name_en": "Software Testing & QA", "slug": "y4-se-qa", "order": 3},
                {"name_ar": "أنماط التصميم البرمجي", "name_en": "Design Patterns", "slug": "y4-se-design-patterns", "order": 4},
                {"name_ar": "إدارة مشاريع البرمجيات", "name_en": "Software Project Management", "slug": "y4-se-project-mgmt", "order": 5},
            ],
            2: [
                {"name_ar": "مشروع هندسة برمجيات", "name_en": "SE Capstone Project", "slug": "y4-se-capstone", "order": 1},
                {"name_ar": "هندسة المتطلبات", "name_en": "Requirements Engineering", "slug": "y4-se-requirements", "order": 2},
                {"name_ar": "التكامل والتسليم المستمر", "name_en": "CI/CD Pipelines", "slug": "y4-se-cicd", "order": 3},
                {"name_ar": "أخلاقيات هندسة البرمجيات", "name_en": "Software Ethics", "slug": "y4-se-ethics", "order": 4},
            ],
        },
        "artificial-intelligence": {
            1: [
                {"name_ar": "التعلم العميق التطبيقي", "name_en": "Applied Deep Learning", "slug": "y4-ai-deep-learning", "order": 1},
                {"name_ar": "معالجة اللغات الطبيعية المتقدمة", "name_en": "Advanced NLP", "slug": "y4-ai-nlp", "order": 2},
                {"name_ar": "الرؤية الحاسوبية المتقدمة", "name_en": "Advanced Computer Vision", "slug": "y4-ai-vision", "order": 3},
                {"name_ar": "الذكاء الاصطناعي التطبيقي", "name_en": "Applied AI", "slug": "y4-ai-applied", "order": 4},
                {"name_ar": "تحليل البيانات الذكي", "name_en": "Intelligent Data Analytics", "slug": "y4-ai-analytics", "order": 5},
            ],
            2: [
                {"name_ar": "التعلم المعزز", "name_en": "Reinforcement Learning", "slug": "y4-ai-rl", "order": 1},
                {"name_ar": "مشروع ذكاء اصطناعي", "name_en": "AI Project", "slug": "y4-ai-project", "order": 2},
                {"name_ar": "أخلاقيات الذكاء الاصطناعي", "name_en": "AI Ethics", "slug": "y4-ai-ethics", "order": 3},
                {"name_ar": "نماذج اللغة الكبيرة", "name_en": "Large Language Models", "slug": "y4-ai-llm", "order": 4},
            ],
        },
        "computer-networks": {
            1: [
                {"name_ar": "شبكات الحاسوب المتقدمة", "name_en": "Advanced Computer Networks", "slug": "y4-net-advanced", "order": 1},
                {"name_ar": "أمن الشبكات", "name_en": "Network Security", "slug": "y4-net-security", "order": 2},
                {"name_ar": "بروتوكولات الإنترنت", "name_en": "Internet Protocols", "slug": "y4-net-protocols", "order": 3},
                {"name_ar": "إدارة ومراقبة الشبكات", "name_en": "Network Management", "slug": "y4-net-management", "order": 4},
                {"name_ar": "الشبكات المعرفة بالبرمجيات SDN", "name_en": "Software-Defined Networking", "slug": "y4-net-sdn", "order": 5},
            ],
            2: [
                {"name_ar": "الأمن السيبراني المتقدم", "name_en": "Advanced Cybersecurity", "slug": "y4-net-cyber", "order": 1},
                {"name_ar": "الشبكات اللاسلكية", "name_en": "Wireless Networks", "slug": "y4-net-wireless", "order": 2},
                {"name_ar": "مراكز البيانات والبنية التحتية", "name_en": "Data Centers & Infrastructure", "slug": "y4-net-datacenter", "order": 3},
                {"name_ar": "مشروع شبكات", "name_en": "Networks Project", "slug": "y4-net-project", "order": 4},
            ],
        },
    },
    "year-5": {
        "software-engineering": {
            1: [
                {"name_ar": "مشروع التخرج - هندسة برمجيات (الأولى)", "name_en": "Graduation Project SE Phase I", "slug": "y5-se-grad-1", "order": 1},
                {"name_ar": "هندسة الأنظمة الموزعة", "name_en": "Distributed Systems Engineering", "slug": "y5-se-distributed", "order": 2},
                {"name_ar": "أداء وتحسين التطبيقات", "name_en": "Application Performance", "slug": "y5-se-performance", "order": 3},
                {"name_ar": "الحاويات والخدمات المصغرة", "name_en": "Containers & Microservices", "slug": "y5-se-microservices", "order": 4},
                {"name_ar": "قابلية التوسع في الأنظمة", "name_en": "Scalable Systems", "slug": "y5-se-scalability", "order": 5},
            ],
            2: [
                {"name_ar": "مشروع التخرج - هندسة برمجيات (النهائية)", "name_en": "Graduation Project SE Phase II", "slug": "y5-se-grad-2", "order": 1},
                {"name_ar": "ريادة الأعمال التقنية", "name_en": "Tech Entrepreneurship", "slug": "y5-se-entrepreneurship", "order": 2},
                {"name_ar": "DevSecOps", "name_en": "DevSecOps", "slug": "y5-se-devsecops", "order": 3},
                {"name_ar": "مهارات التوظيف التقني", "name_en": "Technical Interview Skills", "slug": "y5-se-interviews", "order": 4},
            ],
        },
        "artificial-intelligence": {
            1: [
                {"name_ar": "مشروع التخرج - ذكاء اصطناعي (الأولى)", "name_en": "Graduation Project AI Phase I", "slug": "y5-ai-grad-1", "order": 1},
                {"name_ar": "الذكاء الاصطناعي التوليدي", "name_en": "Generative AI", "slug": "y5-ai-generative", "order": 2},
                {"name_ar": "تحسين نماذج التعلم العميق", "name_en": "DL Model Optimization", "slug": "y5-ai-optimization", "order": 3},
                {"name_ar": "الذكاء الاصطناعي التفسيري", "name_en": "Explainable AI", "slug": "y5-ai-xai", "order": 4},
                {"name_ar": "أنظمة المعلومات الذكية", "name_en": "Intelligent Information Systems", "slug": "y5-ai-intelligent-sys", "order": 5},
            ],
            2: [
                {"name_ar": "مشروع التخرج - ذكاء اصطناعي (النهائية)", "name_en": "Graduation Project AI Phase II", "slug": "y5-ai-grad-2", "order": 1},
                {"name_ar": "الذكاء الاصطناعي في الصناعة", "name_en": "AI in Industry", "slug": "y5-ai-industry", "order": 2},
                {"name_ar": "الروبوتات الذكية", "name_en": "Intelligent Robotics", "slug": "y5-ai-robotics", "order": 3},
                {"name_ar": "مهارات المقابلات التقنية", "name_en": "Technical Interview Skills", "slug": "y5-ai-interviews", "order": 4},
            ],
        },
        "computer-networks": {
            1: [
                {"name_ar": "مشروع التخرج - شبكات (الأولى)", "name_en": "Graduation Project Networks Phase I", "slug": "y5-net-grad-1", "order": 1},
                {"name_ar": "أمن الشبكات المتقدم", "name_en": "Advanced Network Security", "slug": "y5-net-security", "order": 2},
                {"name_ar": "الشبكات السحابية", "name_en": "Cloud Networking", "slug": "y5-net-cloud", "order": 3},
                {"name_ar": "إنترنت الأشياء الصناعي", "name_en": "Industrial IoT", "slug": "y5-net-iot", "order": 4},
                {"name_ar": "مراقبة الشبكات الذكية", "name_en": "Smart Network Monitoring", "slug": "y5-net-monitoring", "order": 5},
            ],
            2: [
                {"name_ar": "مشروع التخرج - شبكات (النهائية)", "name_en": "Graduation Project Networks Phase II", "slug": "y5-net-grad-2", "order": 1},
                {"name_ar": "إدارة البنية التحتية الشبكية", "name_en": "Network Infrastructure Management", "slug": "y5-net-infra", "order": 2},
                {"name_ar": "الشبكات الخلوية 5G", "name_en": "5G Cellular Networks", "slug": "y5-net-5g", "order": 3},
                {"name_ar": "شهادات الشبكات المهنية", "name_en": "Professional Network Certifications", "slug": "y5-net-certs", "order": 4},
            ],
        },
    },
}

SPECIALIZED_YEARS = [
    {
        "year": {"name_ar": "السنة الرابعة", "name_en": "Fourth Year", "slug": "year-4", "order": 4},
        "has_specializations": True,
        "semesters": [
            {"number": 1, "name_ar": "الفصل الأول", "name_en": "Semester 1", "slug": "year-4-sem-1"},
            {"number": 2, "name_ar": "الفصل الثاني", "name_en": "Semester 2", "slug": "year-4-sem-2"},
        ],
    },
    {
        "year": {"name_ar": "السنة الخامسة", "name_en": "Fifth Year", "slug": "year-5", "order": 5},
        "has_specializations": True,
        "semesters": [
            {"number": 1, "name_ar": "الفصل الأول", "name_en": "Semester 1", "slug": "year-5-sem-1"},
            {"number": 2, "name_ar": "الفصل الثاني", "name_en": "Semester 2", "slug": "year-5-sem-2"},
        ],
    },
]

CURRICULUM_DATA = GENERAL_YEARS + SPECIALIZED_YEARS
