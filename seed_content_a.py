# -*- coding: utf-8 -*-
"""
ترجمه‌های دستی و دقیق چهارزبانه محتوای نمونه — بخش اول
(خدمات، اخبار، اسلایدر، بلوک‌های صفحه اصلی، دوره‌ها، نظرات مراجعین)
«src» برای یافتن ردیف در دیتابیس بر اساس متن فارسی است؛ ترجمه روی همه
ردیف‌های منطبق اعمال می‌شود (محتوای تکراری هم پوشش داده می‌شود).
"""

SEEDS_A = [
    # ---------------- خدمات ----------------
    {"table": "services", "src": {"title": "روان درمانی"}, "tr": {
        "en": {"title": "Psychotherapy",
               "subtitle": "Treatment of deep psychological issues",
               "summary": "Psychotherapy helps people face life's challenges, stresses and major decisions with greater awareness. Through an in-depth exploration of the roots of these issues, it provides lasting solutions for improving quality of life."},
        "ar": {"title": "العلاج النفسي",
               "subtitle": "علاج المشكلات النفسية العميقة",
               "summary": "يساعد العلاج النفسي الأفراد على مواجهة تحديات الحياة وضغوطها وقراراتها المصيرية بمزيد من الوعي. ومن خلال دراسة عميقة لجذور المشكلات، يوفر حلولاً مستدامة لتحسين جودة الحياة."},
        "ru": {"title": "Психотерапия",
               "subtitle": "Лечение глубоких психологических проблем",
               "summary": "Психотерапия помогает людям более осознанно справляться с трудностями, стрессом и важными жизненными решениями. Глубокое изучение корней проблем позволяет найти устойчивые решения для повышения качества жизни."},
        "zh": {"title": "心理治疗",
               "subtitle": "治疗深层的心理问题",
               "summary": "心理治疗帮助人们以更清醒的方式应对生活中的挑战、压力和重大决定。通过深入探究问题的根源，为提升生活质量提供持久的解决方案。"}}},

    {"table": "services", "src": {"title": "مشاوره"}, "tr": {
        "en": {"title": "Counseling",
               "subtitle": "An opportunity for better decisions",
               "summary": "Counseling is a supportive process that helps people make better decisions in their personal, professional and family lives with greater awareness. Our counseling focuses on solving everyday issues and improving quality of life."},
        "ar": {"title": "الاستشارة",
               "subtitle": "فرصة لاتخاذ قرارات أفضل",
               "summary": "الاستشارة عملية داعمة تساعد الأفراد على اتخاذ قرارات أفضل في حياتهم الشخصية والعملية والأسرية بمزيد من الوعي. وتركز استشاراتنا على حل مشكلات الحياة اليومية وتحسين جودة الحياة."},
        "ru": {"title": "Консультирование",
               "subtitle": "Возможность принять лучшие решения",
               "summary": "Консультирование — это поддерживающий процесс, который помогает людям более осознанно принимать решения в личной, профессиональной и семейной жизни. Наши консультации сосредоточены на решении повседневных вопросов и повышении качества жизни."},
        "zh": {"title": "心理咨询",
               "subtitle": "做出更好决定的机会",
               "summary": "心理咨询是一个支持性的过程，帮助人们以更高的认知水平在个人、职业和家庭生活中做出更好的决定。我们的咨询专注于解决日常问题、提升生活质量。"}}},

    {"table": "services", "src": {"title": "آموزش"}, "tr": {
        "en": {"title": "Education",
               "subtitle": "Advancing personal and professional knowledge and skills",
               "summary": "Education plays an important role in personal and professional growth. At the Rose (Rose Sefid) Psychology and Counseling Chain Clinics, we offer diverse training courses for the general public, students and professionals, designed to increase awareness, enhance practical skills, strengthen mental health and improve quality of life."},
        "ar": {"title": "التدريب",
               "subtitle": "تطوير المعارف والمهارات الفردية والتخصصية",
               "summary": "يلعب التدريب دوراً مهماً في النمو الفردي والمهني. في عيادات رز المتسلسلة لعلم النفس والمشورة (رز سفيد)، نقدم دورات تدريبية متنوعة لعامة الناس والطلاب والمختصين، مصممة لزيادة الوعي ورفع المهارات العملية وتعزيز الصحة النفسية وتحسين جودة الحياة."},
        "ru": {"title": "Обучение",
               "subtitle": "Развитие личных и профессиональных знаний и навыков",
               "summary": "Обучение играет важную роль в личностном и профессиональном росте. В сети клиник психологии и консультирования «Роз» (Розе Сефид) мы предлагаем разнообразные учебные курсы для широкой публики, студентов и специалистов — они направлены на повышение осведомлённости, развитие практических навыков, укрепление психического здоровья и улучшение качества жизни."},
        "zh": {"title": "教育培训",
               "subtitle": "提升个人与专业知识技能",
               "summary": "教育培训在个人和职业成长中发挥着重要作用。玫瑰（白玫瑰）心理与咨询连锁诊所面向大众、学生和专业人士开设多样化的培训课程，旨在提升认知、强化实用技能、增进心理健康并改善生活质量。"}}},

    {"table": "services", "src": {"title": "سایر خدمات"}, "tr": {
        "en": {"title": "Other Services",
               "subtitle": "Social responsibility and organizational collaborations",
               "summary": "Besides individual, group and educational services, Rose Psychology and Counseling Chain Clinics pay special attention to social commitments and organizational collaborations. Their goal is to create a positive impact on community mental health, transform workplaces into healthier and more productive spaces, and support those in need of psychological care."},
        "ar": {"title": "خدمات أخرى",
               "subtitle": "المسؤولية الاجتماعية والتعاون المؤسسي",
               "summary": "إلى جانب الخدمات الفردية والجماعية والتدريبية، تولي عيادات رز المتسلسلة لعلم النفس والمشورة اهتماماً خاصاً بالالتزامات الاجتماعية والتعاون المؤسسي. وهدفها إحداث أثر إيجابي في الصحة النفسية للمجتمع، وتحويل بيئات العمل إلى فضاءات أكثر صحة وإنتاجية، ودعم من يحتاجون إلى العلاج النفسي."},
        "ru": {"title": "Другие услуги",
               "subtitle": "Социальная ответственность и корпоративное сотрудничество",
               "summary": "Помимо индивидуальных, групповых и образовательных услуг, сеть клиник психологии и консультирования «Роз» уделяет особое внимание социальной ответственности и корпоративному сотрудничеству. Их цель — положительное влияние на психическое здоровье общества, превращение рабочих пространств в более здоровые и продуктивные, а также поддержка тех, кому нужна психологическая помощь."},
        "zh": {"title": "其他服务",
               "subtitle": "社会责任与机构合作",
               "summary": "玫瑰心理与咨询连锁诊所除个人、团体和教育培训服务外，还高度重视社会责任与机构合作，旨在对社区心理健康产生积极影响，将工作环境转变为更健康、更高效的空间，并帮助需要心理支持的人群。"}}},

    # ---------------- اخبار ----------------
    {"table": "news", "src": {"title": "پویش باید برخاست با راه زندگی در تهران، قم و خراسان رضوی"}, "tr": {
        "en": {"title": "The “We Must Rise” campaign with Rah Zendegi in Tehran, Qom and Razavi Khorasan",
               "summary": "Persian summary",
               "content": "Persian text"},
        "ar": {"title": "حملة «يجب أن نهض» مع راه زندگی في طهران وقم وخراسان الرضوي",
               "summary": "الملخص الفارسي",
               "content": "النص الفارسي"},
        "ru": {"title": "Кампания «Надо подняться» вместе с «Рах Зендеги» в Тегеране, Куме и Хорасане-Резави",
               "summary": "Краткое описание (перс.)",
               "content": "Текст (перс.)"},
        "zh": {"title": "“必须奋起”运动——“生活之路”在德黑兰、库姆和礼萨呼罗珊",
               "summary": "波斯语摘要",
               "content": "波斯语正文"}}},

    {"table": "news", "src": {"title": "بازدید هیئت بلندپایه اندونزیایی از ستاد مرکزی مجموعه راه زندگی"}, "tr": {
        "en": {"title": "Visit of a high-ranking Indonesian delegation to the Rah Zendegi headquarters",
               "summary": "A high-ranking delegation of Indonesian officials and representatives, as part of an official program, visited the Rah Zendegi headquarters.",
               "content": "A high-ranking delegation of Indonesian officials and representatives, as part of an official program, visited the Rah Zendegi headquarters. During the visit, the online platform for managing counseling centers, the specialized psychology training system and the experience of the Rose chain clinics were presented to the delegation.\n\nThe two sides discussed expanding international cooperation in mental health, sharing experience in the specialized training of counselors, and using new technologies in delivering psychological services."},
        "ar": {"title": "زيارة وفد إندونيسي رفيع المستوى إلى المقر المركزي لمجموعة راه زندگی",
               "summary": "قام وفد رفيع المستوى من المسؤولين والممثلين الإندونيسيين، في إطار برنامج رسمي، بزيارة المقر المركزي لمجموعة راه زندگی.",
               "content": "قام وفد رفيع المستوى يضم مسؤولين وممثلين إندونيسيين، في إطار برنامج رسمي، بزيارة المقر المركزي لمجموعة راه زندگی. وخلال الزيارة قُدم للوفد منصة الإدارة الإلكترونية لمراكز المشورة، ونظام التدريبات التخصصية لعلم النفس، وتجربة عيادات رز المتسلسلة.\n\nوتبادل الطرفان الحديث حول توسيع التعاون الدولي في مجال الصحة النفسية، وتبادل الخبرات في تدريب المستشارين تخصصياً، واستخدام التقنيات الحديثة في تقديم الخدمات النفسية."},
        "ru": {"title": "Визит высокой индонезийской делегации в центральный офис комплекса «Рах Зендеги»",
               "summary": "Высокопоставленная делегация индонезийских чиновников и представителей в рамках официальной программы посетила центральный офис комплекса «Рах Зендеги».",
               "content": "Высокопоставленная делегация в составе индонезийских чиновников и представителей в рамках официальной программы посетила центральный офис комплекса «Рах Зендеги». В ходе визита делегации были представлены онлайн-платформа управления консультационными центрами, система специализированного обучения психологии и опыт сети клиник «Роз».\n\nСтороны обсудили расширение международного сотрудничества в области психического здоровья, обмен опытом в специализированной подготовке консультантов и применение современных технологий в оказании психологических услуг."},
        "zh": {"title": "印尼高级代表团参观“生活之路”总部",
               "summary": "由印尼官员和代表组成的高级代表团在正式行程中参观了“生活之路”总部。",
               "content": "由印尼官员和代表组成的高级代表团在正式行程中参观了“生活之路”总部。访问期间，代表团了解了咨询中心在线管理平台、心理学专业培训体系以及玫瑰连锁诊所的运营经验。\n\n双方就拓展心理健康领域的国际合作、交流咨询师专业培训经验以及运用新技术提供心理服务进行了探讨。"}}},

    {"table": "news", "src": {"title": "شرکت در هشتمین دوره جایزه ملی تعالی و پیشرفت"}, "tr": {
        "en": {"title": "Participation in the 8th National Excellence and Progress Award",
               "summary": "Iran's National Excellence and Progress Award is an organizational evaluation system based on the Iranian-Islamic model of progress; Rah Zendegi took part in its 8th round.",
               "content": "The National Excellence and Progress Award of the Islamic Republic of Iran is an organizational evaluation system based on the Iranian-Islamic model of progress, in which the country's leading organizations are assessed. Rah Zendegi (Rose Sefid) participated in the 8th round of this national award.\n\nTaking part in the award is an opportunity for independent assessment of organizational processes, identifying strengths and areas for improvement, and moving toward organizational excellence based on the Iranian-Islamic model of progress."},
        "ar": {"title": "المشاركة في الدورة الثامنة لجائزة التميز والتقدم الوطنية",
               "summary": "جائزة التميز والتقدم لجمهورية إيران الإسلامية نظام تقييم مؤسسي مبني على النموذج الإسلامي-الإيراني للتقدم؛ وشاركت مجموعة راه زندگی في الدورة الثامنة من هذه الجائزة.",
               "content": "جائزة التميز والتقدم لجمهورية إيران الإسلامية نظام تقييم مؤسسي مبني على النموذج الإسلامي-الإيراني للتقدم تُقيَّم فيه المنظمات البارزة في البلاد. وشاركت مجموعة راه زندگی (رز سفيد) في الدورة الثامنة من هذه الجائزة الوطنية.\n\nوتمثل المشاركة في هذه الجائزة فرصة لتقييم مستقل للعمليات المؤسسية، وتحديد نقاط القوة والجوانب القابلة للتحسين، والسير على طريق التميز المؤسسي وفقاً للنموذج الإسلامي-الإيراني للتقدم."},
        "ru": {"title": "Участие в 8-м Национальном конкурсе «Совершенство и прогресс»",
               "summary": "Национальная премия «Совершенство и прогресс» Исламской Республики Иран — система организационной оценки на основе исламско-иранской модели прогресса; комплекс «Рах Зендеги» принял участие в её 8-м конкурсе.",
               "content": "Национальная премия «Совершенство и прогресс» Исламской Республики Иран — это система организационной оценки на основе исламско-иранской модели прогресса, в которой оцениваются ведущие организации страны. Комплекс «Рах Зендеги» (Розе Сефид) участвовал в 8-м конкурсе этой национальной премии.\n\nУчастие в премии — это возможность независимой оценки организационных процессов, выявления сильных сторон и направлений улучшения, а также движения к организационному совершенству согласно исламско-иранской модели прогресса."},
        "zh": {"title": "参加第八届国家卓越与进步奖",
               "summary": "伊朗伊斯兰共和国“卓越与进步奖”是基于伊斯兰—伊朗进步模式的组织评估体系；“生活之路”团队参加了第八届评选。",
               "content": "伊朗伊斯兰共和国“卓越与进步奖”是基于伊斯兰—伊朗进步模式、对国内优秀组织进行评估的体系。“生活之路”（白玫瑰）团队参加了本届国家奖项的第八届评选。\n\n参与该奖项有助于独立评估组织流程、发现优势与改进空间，并依据伊斯兰—伊朗进步模式迈向组织卓越。"}}},

    # ---------------- اسلایدر صفحه اصلی ----------------
    {"table": "slides", "src": {"title": "کلینیک‌های زنجیره‌ای روانشناسی و مشاوره رز"}, "tr": {
        "en": {"title": "Rose Psychology & Counseling Chain Clinics",
               "subtitle": "More than 30 active centers across the country; with you on the path to mental health",
               "button_label": "View Centers"},
        "ar": {"title": "عيادات رز المتسلسلة لعلم النفس والمشورة",
               "subtitle": "أكثر من ٣٠ مركزاً نشطاً في أنحاء البلاد؛ معكم في طريق الصحة النفسية",
               "button_label": "مشاهدة المراكز"},
        "ru": {"title": "Сеть клиник психологии и консультирования «Роз»",
               "subtitle": "Более 30 центров по всей стране; рядом с вами на пути к психическому здоровью",
               "button_label": "Наши центры"},
        "zh": {"title": "玫瑰心理与咨询连锁诊所",
               "subtitle": "全国30余家服务中心，与您同行心理健康之路",
               "button_label": "查看中心"}}},

    {"table": "slides", "src": {"title": "آکادمی رز — دوره‌های تخصصی روانشناسی"}, "tr": {
        "en": {"title": "Rose Academy — Specialized Psychology Courses",
               "subtitle": "Specialized workshops and courses with valid certificates; register for courses now",
               "button_label": "View Courses"},
        "ar": {"title": "أكاديمية رز — الدورات التخصصية لعلم النفس",
               "subtitle": "ورش ودورات تخصصية بشهادات معتمدة؛ سجل الآن في الدورات",
               "button_label": "مشاهدة الدورات"},
        "ru": {"title": "Академия «Роз» — специализированные курсы психологии",
               "subtitle": "Специализированные семинары и курсы с действующими сертификатами; зарегистрируйтесь сейчас",
               "button_label": "Курсы"},
        "zh": {"title": "玫瑰学院 — 心理学专业课程",
               "subtitle": "提供权威证书的专业工作坊与课程；立即报名",
               "button_label": "查看课程"}}},

    {"table": "slides", "src": {"title": "دستیار هوشمند رز — پاسخگوی ۲۴ ساعته"}, "tr": {
        "en": {"title": "Rose Smart Assistant — Available 24/7",
               "subtitle": "Ask the smart chat anything about services, courses and centers",
               "button_label": "Start Chat"},
        "ar": {"title": "المساعد الذكي لرز — متاح على مدار الساعة",
               "subtitle": "اسأل الدردشة الذكية عن أي سؤال حول الخدمات والدورات والمراكز",
               "button_label": "ابدأ المحادثة"},
        "ru": {"title": "Умный помощник «Роз» — на связи 24/7",
               "subtitle": "Спрашивайте умный чат обо всём: услуги, курсы, центры",
               "button_label": "Начать чат"},
        "zh": {"title": "玫瑰智能助手 — 全天候在线",
               "subtitle": "关于服务、课程与中心的任何问题，请咨询智能聊天",
               "button_label": "开始对话"}}},

    # ---------------- بلوک‌های صفحه اصلی ----------------
    {"table": "home_blocks", "src": {"title": "درخواست مشاوره"}, "tr": {
        "en": {"title": "Consultation Request", "subtitle": "Quick psychotherapy appointment request"},
        "ar": {"title": "طلب استشارة", "subtitle": "تسجيل سريع لطلب موعد العلاج النفسي"},
        "ru": {"title": "Заявка на консультацию", "subtitle": "Быстрая запись на психотерапию"},
        "zh": {"title": "咨询预约", "subtitle": "快速提交心理治疗预约申请"}}},

    {"table": "home_blocks", "src": {"title": "فراخوان همکاری"}, "tr": {
        "en": {"title": "Cooperation Call", "subtitle": "Register counseling center setup information"},
        "ar": {"title": "دعوة للتعاون", "subtitle": "تسجيل معلومات تأسيس مركز المشورة"},
        "ru": {"title": "Приглашение к сотрудничеству", "subtitle": "Регистрация данных для открытия консультационного центра"},
        "zh": {"title": "合作招募", "subtitle": "登记咨询中心开设信息"}}},

    {"table": "home_blocks", "src": {"title": "پیگیری درخواست"}, "tr": {
        "en": {"title": "Track Request", "subtitle": "Check status with a tracking code"},
        "ar": {"title": "تتبع الطلب", "subtitle": "الاستعلام عن الحالة برمز التتبع"},
        "ru": {"title": "Отслеживание заявки", "subtitle": "Проверка статуса по коду отслеживания"},
        "zh": {"title": "进度查询", "subtitle": "凭跟踪码查询申请状态"}}},

    {"table": "home_blocks", "src": {"title": "پویش باید برخاست"}, "tr": {
        "en": {"title": "“We Must Rise” Campaign", "subtitle": "Psychological support campaign report"},
        "ar": {"title": "حملة «يجب أن نهض»", "subtitle": "تقرير حملة الدعم النفسي"},
        "ru": {"title": "Кампания «Надо подняться»", "subtitle": "Отчёт о кампании психологической поддержки"},
        "zh": {"title": "“必须奋起”运动", "subtitle": "心理支持运动报告"}}},

    {"table": "home_blocks", "src": {"title": "دوره‌های آکادمی رز"}, "tr": {
        "en": {"title": "Rose Academy Courses", "subtitle": "Specialized psychology workshops"},
        "ar": {"title": "دورات أكاديمية رز", "subtitle": "ورش تخصصية لعلم النفس"},
        "ru": {"title": "Курсы Академии «Роз»", "subtitle": "Специализированные семинары по психологии"},
        "zh": {"title": "玫瑰学院课程", "subtitle": "心理学专业工作坊"}}},

    {"table": "home_blocks", "src": {"title": "تبدیل تاریخ شمسی"}, "tr": {
        "en": {"title": "Jalali Date Converter", "subtitle": "Tool for converting Jalali and Gregorian dates"},
        "ar": {"title": "محوّل التاريخ الشمسي", "subtitle": "أداة تحويل بين التقويم الشمسي والميلادي"},
        "ru": {"title": "Конвертер даты Джалали", "subtitle": "Инструмент преобразования дат Джалали и григорианских"},
        "zh": {"title": "波斯历日期转换", "subtitle": "伊朗历（贾拉里历）与公历日期转换工具"}}},

    # ---------------- دوره‌های آموزشی ----------------
    {"table": "courses", "src": {"title": "دوره جامع تنظیم هیجان"}, "tr": {
        "en": {"title": "Comprehensive Emotion Regulation Course",
               "summary": "Practical training in understanding, accepting and managing emotions based on the Gross model; suitable for anyone interested in mental health.",
               "teacher": "Dr. Sara Mohammadi"},
        "ar": {"title": "الدورة الشاملة لتنظيم الانفعالات",
               "summary": "تدريب عملي على مهارات فهم الانفعالات وقبولها وإدارتها وفق نموذج غروس؛ مناسب لعامة المهتمين بالصحة النفسية.",
               "teacher": "د. سارة محمدي"},
        "ru": {"title": "Комплексный курс регуляции эмоций",
               "summary": "Практическое обучение распознаванию, принятию и управлению эмоциями по модели Гросса; подходит всем, кто интересуется психическим здоровьем.",
               "teacher": "Д-р Сара Мохаммади"},
        "zh": {"title": "情绪调节综合课程",
               "summary": "基于格罗斯模型的情绪认知、接纳与管理实用技能培训；适合所有关注心理健康的学员。",
               "teacher": "萨拉·穆罕默迪博士"}}},

    {"table": "courses", "src": {"title": "کارگاه تخصصی درمان شناختی-رفتاری (CBT)"}, "tr": {
        "en": {"title": "Specialized CBT Workshop",
               "summary": "Intensive workshop for professionals and graduate students; CBT techniques for anxiety and depression with role-play and supervision.",
               "teacher": "Dr. Amir Rezaei"},
        "ar": {"title": "ورشة تخصصية في العلاج المعرفي-السلوكي (CBT)",
               "summary": "ورشة مكثفة للمختصين وطلاب الدراسات العليا؛ تدريب تقنيات CBT للقلق والاكتئاب مع تمثيل الأدوار والإشراف.",
               "teacher": "د. أمير رضائي"},
        "ru": {"title": "Специализированный семинар по КПТ (CBT)",
               "summary": "Интенсивный семинар для специалистов и аспирантов; техники КПТ при тревожности и депрессии с ролевыми упражнениями и супервизией.",
               "teacher": "Д-р Амир Резаи"},
        "zh": {"title": "认知行为疗法（CBT）专业工作坊",
               "summary": "面向专业人员和研究生的密集型工作坊；讲授焦虑与抑郁的CBT技术，含角色演练与督导。",
               "teacher": "阿米尔·礼萨伊博士"}}},

    {"table": "courses", "src": {"title": "دوره والدگری مؤثر (تربیت بدون خشونت)"}, "tr": {
        "en": {"title": "Effective Parenting Course (Non-violent Upbringing)",
               "summary": "Skills for healthy communication with children, setting boundaries and managing challenging behaviors based on play-based relationships and a secure maternal/paternal bond.",
               "teacher": "Dr. Maryam Hosseini"},
        "ar": {"title": "دورة التربية الفعالة (التربية بدون عنف)",
               "summary": "مهارات التواصل الصحي مع الطفل وضبط الحدود وإدارة السلوكيات الصعبة اعتماداً على العلاقة باللعب والأمان الأمومي/الأبوي.",
               "teacher": "د. مريم حسيني"},
        "ru": {"title": "Курс эффективного родительства (воспитание без насилия)",
               "summary": "Навыки здорового общения с ребёнком, установления границ и управления сложным поведением на основе игровой связи и надёжной материнской/отцовской привязанности.",
               "teacher": "Д-р Марьям Хоссейни"},
        "zh": {"title": "高效养育课程（无暴力教养）",
               "summary": "基于游戏化关系与安全依恋的亲子沟通、边界设定与挑战性行为管理技能。",
               "teacher": "玛丽亚姆·侯赛尼博士"}}},

    {"table": "courses", "src": {"title": "دوره اجرا و تفسیر آزمون‌های روان‌شناختی"}, "tr": {
        "en": {"title": "Administering and Interpreting Psychological Tests",
               "summary": "Practical training in personality, intelligence and aptitude tests; includes MMPI, WAIS and widely used projective tests.",
               "teacher": "Dr. Reza Karimi"},
        "ar": {"title": "دورة تطبيق وتفسير الاختبارات النفسية",
               "summary": "تدريب عملي على اختبارات الشخصية والذكاء واستكشاف المواهب؛ يشمل اختبارات MMPI وWAIS والاختبارات الإسقاطية الشائعة.",
               "teacher": "د. رضا كريمي"},
        "ru": {"title": "Курс проведения и интерпретации психологических тестов",
               "summary": "Практическое обучение личностным тестам, тестам интеллекта и способностей; включает MMPI, WAIS и распространённые проективные методики.",
               "teacher": "Д-р Реза Карими"},
        "zh": {"title": "心理测验实施与解读课程",
               "summary": "人格、智力与才能测评的实用培训；涵盖MMPI、WAIS及常用投射测验。",
               "teacher": "礼萨·卡里米博士"}}},

    {"table": "courses", "src": {"title": "دوره مدیریت اضطراب", "summary": "آشنایی با مهارت‌های تنظیم اضطراب"}, "tr": {
        "en": {"title": "Anxiety Management Course",
               "summary": "Introduction to anxiety regulation skills",
               "teacher": "Dr. Rezaei"},
        "ar": {"title": "دورة إدارة القلق",
               "summary": "تعريف بمهارات تنظيم القلق",
               "teacher": "د. رضائي"},
        "ru": {"title": "Курс управления тревожностью",
               "summary": "Знакомство с навыками регуляции тревожности",
               "teacher": "Д-р Резаи"},
        "zh": {"title": "焦虑管理课程",
               "summary": "焦虑调节技能入门",
               "teacher": "礼萨伊博士"}}},

    # ---------------- نظرات مراجعین (۴ متن یکتا، هر کدام ۳ بار تکرار شده) ----------------
    {"table": "testimonials", "src": {"text": "«من مدت‌ها بود با اضطراب شدید دست و پنجه نرم می‌کردم. جلسات مشاوره‌ای که اینجا داشتم، واقعا نقطه عطف زندگی من بود. الان آرامش بیشتری دارم و می‌تونم تصمیماتم رو آگاهانه‌تر بگیرم.»"}, "tr": {
        "en": {"name": "Reza Saheb-Nazar",
               "text": "“For a long time I struggled with severe anxiety. The counseling sessions I had here were truly a turning point in my life. I feel calmer now and can make my decisions more consciously.”"},
        "ar": {"name": "رضا صاحب‌نظر",
               "text": "«لزمن طويل كنت أعاني من قلق شديد. كانت جلسات المشورة التي حصلت عليها هنا نقطة تحول حقيقية في حياتي. الآن أشعر بمزيد من الهدوء ويمكنني اتخاذ قراراتي بمزيد من الوعي.»"},
        "ru": {"name": "Реза Сахеб-Назар",
               "text": "«Долгое время я страдал от сильной тревожности. Консультации, которые я проходил здесь, стали настоящим переломным моментом в моей жизни. Теперь я спокоен и принимаю решения более осознанно.»"},
        "zh": {"name": "礼萨·萨赫布纳扎尔",
               "text": "“长期以来我深受严重焦虑困扰。在这里接受的咨询真正成为我人生的转折点。如今我内心更加平静，也能更清醒地做出决定。”"}}},

    {"table": "testimonials", "src": {"text": "«دوره آموزشی تنظیم هیجان واقعاً فراتر از انتظارم بود. محتوای علمی، ساده و کاربردی بود و باعث شد بهتر بتونم خودم رو در موقعیت‌های تنش‌زا مدیریت کنم.»"}, "tr": {
        "en": {"name": "Saman Abbaspor",
               "text": "“The emotion regulation course truly exceeded my expectations. The content was scientific, simple and practical, and it helped me manage myself better in stressful situations.”"},
        "ar": {"name": "سامان عباس‌پور",
               "text": "«تجاوزت دورة تنظيم الانفعالات توقعاتي؛ محتواها علمي وبسيط وعملي، وساعدني على إدارة نفسي بشكل أفضل في المواقف المتوترة.»"},
        "ru": {"name": "Саман Аббаспур",
               "text": "«Курс регуляции эмоций превзошёл мои ожидания. Материал научный, простой и практичный — он помог мне лучше владеть собой в стрессовых ситуациях.»"},
        "zh": {"name": "萨曼·阿巴斯普尔",
               "text": "“情绪调节课程超出了我的预期。内容科学、简明而实用，让我在紧张情境中能更好地自我调节。”"}}},

    {"table": "testimonials", "src": {"text": "«مشاورم با حوصله و بدون قضاوت به حرف‌هام گوش می‌داد. احساس امنیتی که در جلسات تجربه کردم، برام بی‌نظیر بود. ممنونم که کمک کردین به خودم برگردم.»"}, "tr": {
        "en": {"name": "Morteza Rahbari",
               "text": "“My counselor listened to me patiently and without judgment. The sense of safety I experienced in the sessions was unlike anything else. Thank you for helping me return to myself.”"},
        "ar": {"name": "مرتضى رهبري",
               "text": "«كان مستشاري يستمع إليّ بصبر ودون حكم مسبق. كان الشعور بالأمان الذي عشته في الجلسات لا يُقدّر بثمن. شكراً لمساعدتني على العودة إلى نفسي.»"},
        "ru": {"name": "Мортеза Рахбари",
               "text": "«Мой консультант слушал меня терпеливо и без осуждения. Ощущение безопасности, которое я испытывал на сессиях, было для меня бесценным. Спасибо, что помогли мне вернуться к себе.»"},
        "zh": {"name": "莫尔塔扎·拉赫巴里",
               "text": "“我的咨询师耐心而毫无评判地倾听我。会谈中体验到的安全感对我来说无比珍贵。感谢你们帮助我找回自我。”"}}},

    {"table": "testimonials", "src": {"text": "«من و همسرم برای بهبود ارتباطمون به مشاوره زوج‌درمانی مراجعه کردیم. راهکارهایی که بهمون داده شد عملی و مفید بودن. الان گفت‌وگوهامون سالم‌تر شده و کمتر وارد تنش می‌شیم.»"}, "tr": {
        "en": {"name": "Maryam Rahimi",
               "text": "“My spouse and I came to couples therapy to improve our relationship. The solutions we were given were practical and helpful. Now our conversations are healthier and we get into tension less often.”"},
        "ar": {"name": "مريم رحيمي",
               "text": "«أتيت أنا وزوجي إلى استشارة الأزواج لتحسين علاقتنا. كانت الحلول المقدمة لنا عملية ومفيدة. أصبحت حواراتنا الآن أكثر صحة ونلج أقل إلى التوتر.»"},
        "ru": {"name": "Марьям Рахими",
               "text": "«Мы с супругом обратились к парной терапии, чтобы улучшить наши отношения. Предложенные нам решения были практичными и полезными. Теперь наши разговоры стали здоровее, и мы реже впадаем в напряжение.»"},
        "zh": {"name": "玛丽亚姆·拉希米",
               "text": "“我和丈夫为改善夫妻关系参加了伴侣治疗。所提供的方案实用而有效。如今我们的沟通更加健康，陷入冲突的次数也减少了。”"}}},
]
