"""Build the sample school from scratch. Run: python seed.py  (wipes and refills school.db)"""
import os, random
from datetime import date, timedelta
import db
import stats
from jalali import jstr

random.seed(1405)  # same data every time

TERM_START = date(2026, 9, 23)                                    # 1405/07/01
TODAY = date.fromisoformat(os.getenv("DEMO_TODAY", "2026-12-21"))  # 1405/09/30, end of Azar
SCHOOL_DAYS = [TERM_START + timedelta(d) for d in range((TODAY - TERM_START).days + 1)
               if (TERM_START + timedelta(d)).weekday() in (5, 6, 0, 1, 2)]  # Saturday..Wednesday

TEACHERS = [  # (name, subject); first two are homeroom teachers
    ("سارا احمدی", "آموزگار پایه چهارم"), ("مریم رضایی", "آموزگار پایه پنجم"),
    ("نرگس کریمی", "ورزش"), ("زهرا موسوی", "قرآن"), ("لیلا حسینی", "هنر"),
    ("فاطمه نوری", "زبان انگلیسی"), ("الهام صادقی", "علوم آزمایشگاهی"), ("شیما رحیمی", "رایانه و هوش مصنوعی"),
]
LATE_TEACHER = 3  # نرگس کریمی: planted pattern, late three times in Azar

HOMEROOM_SUBJECTS = ["ریاضی", "فارسی", "علوم تجربی", "مطالعات اجتماعی", "هدیه‌های آسمان"]
SPECIAL_SUBJECTS = {"ورزش": 3, "قرآن": 4, "هنر": 5, "زبان انگلیسی": 6}

FIRST = ["آوا", "نازنین", "ریحانه", "فاطمه", "زهرا", "یسنا", "هلیا", "باران", "رها", "نیایش",
         "مهسا", "سارینا", "آیدا", "پرنیا", "ستایش", "کیانا", "محدثه", "النا", "دینا", "مبینا",
         "ترانه", "یکتا", "آرتمیس", "حنانه", "ملیکا", "آیلین", "روژان", "تینا", "غزل", "نگار"]
LAST = ["محمدی", "جعفری", "اکبری", "قاسمی", "طاهری", "عباسی", "مرادی", "نجفی", "صالحی", "یزدانی",
        "فرهادی", "کاظمی", "شریفی", "بهرامی", "توکلی", "زمانی", "حیدری", "رستمی", "سلیمانی", "امیری",
        "نوروزی", "باقری", "فتحی", "ملکی", "رنجبر", "خلیلی", "پاکزاد", "داوودی", "عسگری", "میرزایی"]
FATHERS = ["رضا", "علی", "محمد", "حسین", "مهدی", "امیر", "حمید", "سعید", "مجید", "وحید"]

DECLINING_STUDENT = 1  # آوا محمدی: math drops from Mehr to Azar
ABSENT_STUDENT = 2     # نازنین جعفری: absences jump in Azar

def month_of(d):
    return int(jstr(d)[5:7])

def run():
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    with db.conn() as c:
        c.executescript(db.SCHEMA)

        for name, subject in TEACHERS:
            c.execute("INSERT INTO teachers (full_name, subject, gender) VALUES (?, ?, 'f')", (name, subject))
        c.execute("INSERT INTO classes (name, grade, homeroom_teacher_id) VALUES ('چهارم الف', 4, 1)")
        c.execute("INSERT INTO classes (name, grade, homeroom_teacher_id) VALUES ('پنجم الف', 5, 2)")

        # 30 students, 15 per class. Students 1 and 2 carry the planted stories.
        for i in range(30):
            class_id = 1 if i < 15 else 2
            if i == 1:
                class_id = 2  # نازنین in the fifth grade
            if i == 15:
                class_id = 1
            phone = f"0912{random.randint(1000000, 9999999)}"
            c.execute("""INSERT INTO students (first_name, last_name, gender, class_id, parent_name, parent_phone)
                         VALUES (?, ?, 'f', ?, ?, ?)""",
                      (FIRST[i], LAST[i], class_id, f"{random.choice(FATHERS)} {LAST[i]}", phone))
        students = c.execute("SELECT id, class_id FROM students").fetchall()

        # Assessments: two per month per subject, descriptive level 1..4
        assess_days = [d for d in SCHOOL_DAYS if jstr(d)[8:] in ("12", "13", "14", "26", "27", "28")]
        assess_days = sorted({(month_of(d), jstr(d)[8:] < "20"): d for d in assess_days}.values())
        for s in students:
            base = {sub: random.choice([3, 3, 4, 4, 2]) for sub in HOMEROOM_SUBJECTS + list(SPECIAL_SUBJECTS)}
            for n, d in enumerate(assess_days):
                for sub, lvl in base.items():
                    level = max(1, min(4, lvl + random.choice([0, 0, 0, 1, -1])))
                    if s["id"] == DECLINING_STUDENT and sub == "ریاضی":
                        level = [4, 4, 3, 3, 2, 2][min(n, 5)]
                    teacher = s["class_id"] if sub in HOMEROOM_SUBJECTS else SPECIAL_SUBJECTS[sub]
                    note = "در حل مسائل کسری و تقسیم دچار اشکال شده است." if (
                        s["id"] == DECLINING_STUDENT and sub == "ریاضی" and level == 2) else None
                    c.execute("""INSERT INTO assessments (student_id, subject, date, jdate, level, teacher_id, note)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
                              (s["id"], sub, d.isoformat(), jstr(d), level, teacher, note))

        # Student attendance
        azar_days = [d for d in SCHOOL_DAYS if month_of(d) == 9]
        absent_azar = set(random.sample(azar_days[-14:], 6))
        for s in students:
            for d in SCHOOL_DAYS:
                r = random.random()
                status = "absent" if r < 0.025 else "late" if r < 0.05 else "present"
                if s["id"] == ABSENT_STUDENT:
                    status = "absent" if d in absent_azar else ("present" if status == "absent" else status)
                excused = 1 if status == "absent" and random.random() < 0.6 and s["id"] != ABSENT_STUDENT else 0
                c.execute("""INSERT INTO student_attendance (student_id, date, jdate, status, excused)
                             VALUES (?, ?, ?, ?, ?)""", (s["id"], d.isoformat(), jstr(d), status, excused))

        # Teacher check-in / check-out. Required arrival: 07:30
        late_days = set(random.sample(azar_days[-15:], 3))
        for t in range(1, len(TEACHERS) + 1):
            for d in SCHOOL_DAYS:
                check_in = f"07:{random.randint(10, 29):02d}"
                if t == LATE_TEACHER and d in late_days:
                    check_in = random.choice(["07:48", "07:55", "08:06"])
                check_out = f"13:{random.randint(30, 59):02d}"
                c.execute("""INSERT INTO teacher_attendance (teacher_id, date, jdate, check_in, check_out)
                             VALUES (?, ?, ?, ?, ?)""", (t, d.isoformat(), jstr(d), check_in, check_out))

        # Make "today" itself interesting for the demo: two absences, one late student, one late teacher
        t = TODAY.isoformat()
        c.execute("UPDATE student_attendance SET status='present', excused=0 WHERE date = ?", (t,))
        c.execute("UPDATE student_attendance SET status='absent' WHERE date = ? AND student_id IN (?, 12)", (t, ABSENT_STUDENT))
        c.execute("UPDATE student_attendance SET status='late' WHERE date = ? AND student_id = 24", (t,))
        c.execute("UPDATE teacher_attendance SET check_in='07:42' WHERE date = ? AND teacher_id = 6", (t,))

        # Counselor notes
        notes = [
            (ABSENT_STUDENT, date(2026, 12, 15), "در گفت‌وگوی کوتاه کم‌حرف بود و گفت این روزها حوصله مدرسه آمدن ندارد. پیگیری با خانواده لازم است."),
            (DECLINING_STUDENT, date(2026, 11, 20), "از ریاضی اظهار نگرانی کرد. پیشنهاد شد با آموزگار درباره تمرین بیشتر کسرها صحبت شود."),
            (5, date(2026, 10, 28), "سازگاری خوبی با کلاس جدید دارد."),
            (18, date(2026, 11, 10), "در کار گروهی نقش رهبری دارد. استعداد هنری قابل توجه."),
        ]
        for sid, d, text in notes:
            c.execute("INSERT INTO counselor_notes (student_id, date, jdate, note) VALUES (?, ?, ?, ?)",
                      (sid, d.isoformat(), jstr(d), text))

        # Health and wellbeing forms filled by parents (sample data, not real)
        import json
        forms = [
            (DECLINING_STUDENT, "physical", date(2026, 10, 5), {"height": 138, "weight": 33, "vision": "عادی", "glasses": "خیر",
             "allergy": "ندارد", "condition": "ندارد", "medication": "ندارد", "sleep_hours": 9, "breakfast": "هر روز"}),
            (DECLINING_STUDENT, "wellbeing", date(2026, 10, 5), {"mood": 4, "sleep_quality": 4, "school_worry": 2, "friends": 4,
             "screen_hours": 1, "note": "بچه شاد و پرانرژی است."}),
            (ABSENT_STUDENT, "physical", date(2026, 10, 7), {"height": 145, "weight": 38, "vision": "عادی", "glasses": "خیر",
             "allergy": "گرده گل", "condition": "ندارد", "medication": "ندارد", "sleep_hours": 7, "breakfast": "گاهی"}),
            (ABSENT_STUDENT, "wellbeing", date(2026, 12, 14), {"mood": 2, "sleep_quality": 2, "school_worry": 4, "friends": 2,
             "screen_hours": 4, "note": "این چند هفته صبح‌ها برای آمدن به مدرسه بهانه می‌گیرد."}),
        ]
        for sid, kind, d, data in forms:
            c.execute("""INSERT INTO health_forms (student_id, kind, data, filled_by, date, jdate, created_at, flags)
                         VALUES (?, ?, ?, NULL, ?, ?, ?, ?)""",
                      (sid, kind, json.dumps(data, ensure_ascii=False), d.isoformat(), jstr(d), jstr(d), None))

        # Administrative letters. category/summary/assignee stay empty for the agent to fill later.
        R = "اداره آموزش و پرورش منطقه"
        letters = [
            (date(2026, 11, 3), R, "درخواست آمار ماهانه غیبت دانش‌آموزان (مهرماه)", "خواهشمند است آمار غیبت دانش‌آموزان در مهرماه را به تفکیک پایه تا تاریخ ۱۵ آبان ارسال فرمایید.", date(2026, 11, 6), "done"),
            (date(2026, 12, 2), R, "درخواست آمار ماهانه غیبت دانش‌آموزان (آبان‌ماه)", "خواهشمند است آمار غیبت دانش‌آموزان در آبان‌ماه را به تفکیک پایه تا تاریخ ۱۵ آذر ارسال فرمایید.", date(2026, 12, 6), "done"),
            (date(2026, 12, 18), R, "درخواست آمار دانش‌آموزان به تفکیک پایه", "به منظور برنامه‌ریزی سال آینده، تعداد دانش‌آموزان هر پایه و تعداد کلاس‌ها را تا تاریخ ۳ دی اعلام فرمایید.", date(2026, 12, 24), "new"),
            (date(2026, 12, 20), R, "درخواست آمار ماهانه غیبت دانش‌آموزان (آذرماه)", "خواهشمند است آمار غیبت دانش‌آموزان در آذرماه را به تفکیک پایه تا تاریخ ۵ دی ارسال فرمایید.", date(2026, 12, 26), "new"),
            (date(2026, 12, 7), R, "بخشنامه ساعت کاری زمستانی مدارس", "بدین‌وسیله ساعت شروع کلاس‌ها از ۱۵ آذر تا پایان بهمن ساعت ۸:۰۰ تعیین می‌شود. اعلام وصول این بخشنامه الزامی است.", None, "new"),
            (date(2026, 12, 9), R, "بخشنامه طرح ملی سنجش بینایی دانش‌آموزان", "طرح سنجش بینایی پایه اول در دی‌ماه اجرا می‌شود. لطفا وصول این بخشنامه را اعلام کنید.", None, "new"),
            (date(2026, 12, 14), R, "دستورالعمل پیش‌ثبت‌نام سال تحصیلی ۱۴۰۶-۱۴۰۵", "دستورالعمل پیوست برای اطلاع و اجرا ارسال می‌شود. اعلام وصول آن ضروری است.", None, "new"),
            (date(2026, 12, 10), R, "دعوت مدیران به جلسه هم‌اندیشی", "جلسه هم‌اندیشی مدیران مدارس غیردولتی روز ۷ دی ساعت ۹ در سالن اداره برگزار می‌شود. حضور مدیر محترم الزامی است.", date(2026, 12, 28), "new"),
            (date(2026, 12, 11), R, "بخشنامه ایمنی وسایل گرمایشی مدارس", "رعایت نکات ایمنی وسایل گرمایشی و بازدید دوره‌ای آن‌ها الزامی است. چک‌لیست بازدید پیوست است.", None, "new"),
            (date(2026, 12, 12), "مؤسسه علمی کاوش", "پیشنهاد برگزاری اردوی علمی رصد آسمان", "این مؤسسه آمادگی دارد اردوی یک‌روزه رصد آسمان را برای پایه‌های چهارم تا ششم با هزینه هر نفر ۱۸۰ هزار تومان برگزار کند.", None, "new"),
            (date(2026, 12, 13), "شرکت نوین‌تحریر", "پیشنهاد قرارداد تأمین لوازم‌التحریر", "پیشنهاد قرارداد یک‌ساله تأمین لوازم‌التحریر مدرسه با ۱۵ درصد تخفیف ارسال می‌شود. خواهشمند است نتیجه بررسی را اعلام فرمایید.", date(2027, 1, 5), "new"),
            (date(2026, 12, 15), R, "درخواست معرفی آموزگار نمونه", "لطفا یک نفر از آموزگاران شایسته را به همراه سوابق تا تاریخ ۱۰ دی معرفی فرمایید.", date(2026, 12, 31), "new"),
            (date(2026, 12, 16), "بیمه آسیا", "یادآوری تمدید بیمه حوادث دانش‌آموزان", "مهلت تمدید بیمه حوادث دانش‌آموزان تا ۱۵ دی است. لطفا فهرست دانش‌آموزان را ارسال کنید.", date(2027, 1, 5), "new"),
            (date(2026, 12, 17), "ولی دانش‌آموز پایه پنجم", "درخواست تغییر مسیر سرویس", "به دلیل تغییر محل سکونت، درخواست دارم مسیر سرویس فرزندم از ابتدای دی تغییر کند.", None, "new"),
            (date(2026, 12, 20), "دبیرخانه مسابقات علمی دانش‌آموزی", "فراخوان مسابقه هوش مصنوعی دانش‌آموزی", "مسابقه کشوری «هوش مصنوعی برای کودکان» برای دانش‌آموزان پایه‌های چهارم تا ششم برگزار می‌شود. خواهشمند است دو دانش‌آموز علاقه‌مند به همراه یک معلم راهنما را تا ۴ دی معرفی فرمایید. اطلاع‌رسانی به اولیای دانش‌آموزان نیز توصیه می‌شود.", date(2026, 12, 25), "new"),
            (date(2026, 12, 19), R, "اطلاعیه کارگاه آموزشی ارزشیابی توصیفی", "کارگاه ارزشیابی توصیفی برای آموزگاران روز ۱۲ دی برگزار می‌شود. معرفی شرکت‌کنندگان تا ۵ دی.", date(2026, 12, 26), "new"),
        ]
        for d, sender, subject, body, deadline, status in letters:
            c.execute("""INSERT INTO letters (received_date, jreceived, sender, subject, body, deadline, jdeadline, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (d.isoformat(), jstr(d), sender, subject, body,
                       deadline.isoformat() if deadline else None, jstr(deadline) if deadline else None, status))

        # The two earlier monthly absence requests were answered by staff, by hand.
        # Their replies use the real numbers, so the agent can learn the format from them.
        for month, name in ((7, "مهر"), (8, "آبان")):
            reply = stats.to_fa("با سلام و احترام\nدر پاسخ به نامه شما، " + stats.absence_text(c, month) +
                                "\nبا احترام، مدیریت دبستان جاوید")
            c.execute("""UPDATE letters SET category = 'stats', summary = ?, reply = ?, handled_at = ?
                         WHERE subject LIKE ?""",
                      (f"درخواست آمار غیبت {name}‌ماه به تفکیک پایه", reply, "پاسخ داده شده توسط کارمند اداری",
                       f"%({name}%"))

        # Login users. Every password is 1234.
        users = [
            ("modir", "آقای دکتر انوشه‌پور", "manager", None),
            ("edari", "کارمند اداری نمونه", "staff", None),
            ("moalem", "سارا احمدی", "teacher", 1),
            ("karimi", "نرگس کریمی", "teacher", LATE_TEACHER),
            ("moshaver", "مریم کاظمی", "counselor", None),
            ("vali", "رضا محمدی (ولیِ آوا)", "parent", DECLINING_STUDENT),
            ("daneshamooz", "آوا محمدی", "student", DECLINING_STUDENT),
        ]
        # Accounts for every other teacher and parent, so letters can be referred to anyone
        taken_teachers = {r for _, _, role, r in users if role == "teacher"}
        for tid, name in c.execute("SELECT id, full_name FROM teachers").fetchall():
            if tid not in taken_teachers:
                users.append((f"teacher{tid}", name, "teacher", tid))
        for sid, first, last, parent in c.execute("SELECT id, first_name, last_name, parent_name FROM students").fetchall():
            if sid != DECLINING_STUDENT:
                users.append((f"parent{sid}", f"{parent} (ولیِ {first})", "parent", sid))
        pw = db.hash_password("1234")
        for username, full_name, role, ref in users:
            c.execute("INSERT INTO users (username, password, full_name, role, ref_id) VALUES (?, ?, ?, ?, ?)",
                      (username, pw, full_name, role, ref))
    print(f"school.db ready: {len(SCHOOL_DAYS)} school days, today = {jstr(TODAY)}")

if __name__ == "__main__":
    run()
