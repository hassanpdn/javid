"""Build the sample school from scratch. Run: python seed.py  (wipes and refills school.db)"""
import os, random
from datetime import date, timedelta
import db
import stats
from jalali import jstr, to_jalali, to_gregorian, MONTHS

random.seed(1405)  # same data every time (for the same "today")

# Everything is built relative to today, so the demo is right on whatever day it runs.
# DEMO_TODAY=2026-10-25 in .env pins a date (handy for screenshots and tests).
TODAY = date.fromisoformat(os.getenv("DEMO_TODAY") or date.today().isoformat())
JY, JM, JD = to_jalali(TODAY)
TERM_START = to_gregorian(JY if JM >= 7 else JY - 1, 7, 1)        # 1 Mehr of this school year
# Saturday..Wednesday are school days. Today always counts, so the dashboard has a "today" even on a weekend.
SCHOOL_DAYS = [TERM_START + timedelta(d) for d in range((TODAY - TERM_START).days + 1)
               if (TERM_START + timedelta(d)).weekday() in (5, 6, 0, 1, 2) or TERM_START + timedelta(d) == TODAY]

def jday(d):
    """'5 دی' style date for letter texts, with Persian digits."""
    y, m, dd = to_jalali(d)
    return stats.to_fa(f"{dd} {MONTHS[m - 1]}")

def ago(n):
    return TODAY - timedelta(days=n)

def ahead(n):
    return TODAY + timedelta(days=n)

THIS_MONTH, LAST_MONTH = MONTHS[JM - 1], MONTHS[(JM - 2) % 12]

TEACHERS = [  # (name, subject); first two are homeroom teachers
    ("سارا احمدی", "آموزگار پایه چهارم"), ("مریم رضایی", "آموزگار پایه پنجم"),
    ("نرگس کریمی", "ورزش"), ("زهرا موسوی", "قرآن"), ("لیلا حسینی", "هنر"),
    ("فاطمه نوری", "زبان انگلیسی"), ("الهام صادقی", "علوم آزمایشگاهی"), ("شیما رحیمی", "رایانه و هوش مصنوعی"),
]
LATE_TEACHER = 3  # نرگس کریمی: planted pattern, late three times in the last weeks

HOMEROOM_SUBJECTS = ["ریاضی", "فارسی", "علوم تجربی", "مطالعات اجتماعی", "هدیه‌های آسمان"]
SPECIAL_SUBJECTS = {"ورزش": 3, "قرآن": 4, "هنر": 5, "زبان انگلیسی": 6}

FIRST = ["آوا", "نازنین", "ریحانه", "فاطمه", "زهرا", "یسنا", "هلیا", "باران", "رها", "نیایش",
         "مهسا", "سارینا", "آیدا", "پرنیا", "ستایش", "کیانا", "محدثه", "النا", "دینا", "مبینا",
         "ترانه", "یکتا", "آرتمیس", "حنانه", "ملیکا", "آیلین", "روژان", "تینا", "غزل", "نگار"]
LAST = ["محمدی", "جعفری", "اکبری", "قاسمی", "طاهری", "عباسی", "مرادی", "نجفی", "صالحی", "یزدانی",
        "فرهادی", "کاظمی", "شریفی", "بهرامی", "توکلی", "زمانی", "حیدری", "رستمی", "سلیمانی", "امیری",
        "نوروزی", "باقری", "فتحی", "ملکی", "رنجبر", "خلیلی", "پاکزاد", "داوودی", "عسگری", "میرزایی"]
FATHERS = ["رضا", "علی", "محمد", "حسین", "مهدی", "امیر", "حمید", "سعید", "مجید", "وحید"]

DECLINING_STUDENT = 1  # آوا محمدی: math drops since the start of the year
ABSENT_STUDENT = 2     # نازنین جعفری: many absences in the last two weeks

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

        # Assessments: about one every five school days per subject (at least three), descriptive level 1..4
        past = SCHOOL_DAYS[:-1] or SCHOOL_DAYS
        step = max(1, min(5, len(past) // 3))
        assess_days = past[step - 1::step][-8:]
        for s in students:
            base = {sub: random.choice([3, 3, 4, 4, 2]) for sub in HOMEROOM_SUBJECTS + list(SPECIAL_SUBJECTS)}
            for n, d in enumerate(assess_days):
                for sub, lvl in base.items():
                    level = max(1, min(4, lvl + random.choice([0, 0, 0, 1, -1])))
                    if s["id"] == DECLINING_STUDENT and sub == "ریاضی":   # from 4 at the start down to 2 now
                        level = round(4 - 2 * n / max(1, len(assess_days) - 1))
                    teacher = s["class_id"] if sub in HOMEROOM_SUBJECTS else SPECIAL_SUBJECTS[sub]
                    note = "در حل مسائل کسری و تقسیم دچار اشکال شده است." if (
                        s["id"] == DECLINING_STUDENT and sub == "ریاضی" and level == 2) else None
                    c.execute("""INSERT INTO assessments (student_id, subject, date, jdate, level, teacher_id, note)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
                              (s["id"], sub, d.isoformat(), jstr(d), level, teacher, note))

        # Student attendance
        recent = SCHOOL_DAYS[-11:-1]          # the last two weeks, without today
        absent_recent = set(random.sample(recent, min(6, len(recent))))
        for s in students:
            for d in SCHOOL_DAYS:
                r = random.random()
                status = "absent" if r < 0.025 else "late" if r < 0.05 else "present"
                if s["id"] == ABSENT_STUDENT:
                    status = "absent" if d in absent_recent else ("present" if status == "absent" else status)
                excused = 1 if status == "absent" and random.random() < 0.6 and s["id"] != ABSENT_STUDENT else 0
                c.execute("""INSERT INTO student_attendance (student_id, date, jdate, status, excused)
                             VALUES (?, ?, ?, ?, ?)""", (s["id"], d.isoformat(), jstr(d), status, excused))

        # Teacher check-in / check-out. Required arrival: 07:30
        late_days = set(random.sample(recent, min(3, len(recent))))
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
            (ABSENT_STUDENT, ago(4), "در گفت‌وگوی کوتاه کم‌حرف بود و گفت این روزها حوصله مدرسه آمدن ندارد. پیگیری با خانواده لازم است."),
            (DECLINING_STUDENT, ago(9), "از ریاضی اظهار نگرانی کرد. پیشنهاد شد با آموزگار درباره تمرین بیشتر کسرها صحبت شود."),
            (5, ago(20), "سازگاری خوبی با کلاس جدید دارد."),
            (18, ago(15), "در کار گروهی نقش رهبری دارد. استعداد هنری قابل توجه."),
        ]
        for sid, d, text in notes:
            c.execute("INSERT INTO counselor_notes (student_id, date, jdate, note) VALUES (?, ?, ?, ?)",
                      (sid, d.isoformat(), jstr(d), text))

        # Health and wellbeing forms filled by parents (sample data, not real)
        import json
        forms = [
            (DECLINING_STUDENT, "physical", ago(25), {"height": 138, "weight": 33, "vision": "عادی", "glasses": "خیر",
             "allergy": "ندارد", "condition": "ندارد", "medication": "ندارد", "sleep_hours": 9, "breakfast": "هر روز"}),
            (DECLINING_STUDENT, "wellbeing", ago(25), {"mood": 4, "sleep_quality": 4, "school_worry": 2, "friends": 4,
             "screen_hours": 1, "note": "بچه شاد و پرانرژی است."}),
            (ABSENT_STUDENT, "physical", ago(23), {"height": 145, "weight": 38, "vision": "عادی", "glasses": "خیر",
             "allergy": "گرده گل", "condition": "ندارد", "medication": "ندارد", "sleep_hours": 7, "breakfast": "گاهی"}),
            (ABSENT_STUDENT, "wellbeing", ago(5), {"mood": 2, "sleep_quality": 2, "school_worry": 4, "friends": 2,
             "screen_hours": 4, "note": "این چند هفته صبح‌ها برای آمدن به مدرسه بهانه می‌گیرد."}),
        ]
        for sid, kind, d, data in forms:
            c.execute("""INSERT INTO health_forms (student_id, kind, data, filled_by, date, jdate, created_at, flags)
                         VALUES (?, ?, ?, NULL, ?, ?, ?, ?)""",
                      (sid, kind, json.dumps(data, ensure_ascii=False), d.isoformat(), jstr(d), jstr(d), None))

        # Administrative letters. category/summary/assignee stay empty for the agent to fill later.
        R = "اداره آموزش و پرورش منطقه"
        # (received, sender, subject, body, deadline, status). Dates are relative to today; the texts name them.
        letters = [
            (ago(10), R, f"درخواست آمار ماهانه غیبت دانش‌آموزان ({LAST_MONTH}‌ماه)",
             f"خواهشمند است آمار غیبت دانش‌آموزان در {LAST_MONTH}‌ماه را به تفکیک پایه تا تاریخ {jday(ahead(4))} ارسال فرمایید.", ahead(4), "new"),
            (ago(6), R, "درخواست آمار دانش‌آموزان به تفکیک پایه",
             f"به منظور برنامه‌ریزی سال آینده، تعداد دانش‌آموزان هر پایه و تعداد کلاس‌ها را تا تاریخ {jday(ahead(3))} اعلام فرمایید.", ahead(3), "new"),
            (ago(16), R, "بخشنامه ساعت کاری زمستانی مدارس",
             "بدین‌وسیله ساعت شروع کلاس‌ها از ۱۵ آذر تا پایان بهمن ساعت ۸:۰۰ تعیین می‌شود. اعلام وصول این بخشنامه الزامی است.", None, "new"),
            (ago(14), R, "بخشنامه طرح ملی سنجش بینایی دانش‌آموزان",
             "طرح سنجش بینایی پایه اول در ماه آینده اجرا می‌شود. لطفا وصول این بخشنامه را اعلام کنید.", None, "new"),
            (ago(9), R, f"دستورالعمل پیش‌ثبت‌نام سال تحصیلی {stats.to_fa(str(JY + 1))}-{stats.to_fa(str(JY))}",
             "دستورالعمل پیوست برای اطلاع و اجرا ارسال می‌شود. اعلام وصول آن ضروری است.", None, "new"),
            (ago(13), R, "دعوت مدیران به جلسه هم‌اندیشی",
             f"جلسه هم‌اندیشی مدیران مدارس غیردولتی روز {jday(ahead(7))} ساعت ۹ در سالن اداره برگزار می‌شود. حضور مدیر محترم الزامی است.", ahead(7), "new"),
            (ago(12), R, "بخشنامه ایمنی وسایل گرمایشی مدارس",
             "رعایت نکات ایمنی وسایل گرمایشی و بازدید دوره‌ای آن‌ها الزامی است. چک‌لیست بازدید پیوست است.", None, "new"),
            (ago(11), "مؤسسه علمی کاوش", "پیشنهاد برگزاری اردوی علمی رصد آسمان",
             "این مؤسسه آمادگی دارد اردوی یک‌روزه رصد آسمان را برای پایه‌های چهارم تا ششم با هزینه هر نفر ۱۸۰ هزار تومان برگزار کند.", None, "new"),
            (ago(10), "شرکت نوین‌تحریر", "پیشنهاد قرارداد تأمین لوازم‌التحریر",
             "پیشنهاد قرارداد یک‌ساله تأمین لوازم‌التحریر مدرسه با ۱۵ درصد تخفیف ارسال می‌شود. خواهشمند است نتیجه بررسی را اعلام فرمایید.", ahead(15), "new"),
            (ago(8), R, "درخواست معرفی آموزگار نمونه",
             f"لطفا یک نفر از آموزگاران شایسته را به همراه سوابق تا تاریخ {jday(ahead(10))} معرفی فرمایید.", ahead(10), "new"),
            (ago(7), "بیمه آسیا", "یادآوری تمدید بیمه حوادث دانش‌آموزان",
             f"مهلت تمدید بیمه حوادث دانش‌آموزان تا {jday(ahead(15))} است. لطفا فهرست دانش‌آموزان را ارسال کنید.", ahead(15), "new"),
            (ago(6), "ولی دانش‌آموز پایه پنجم", "درخواست تغییر مسیر سرویس",
             "به دلیل تغییر محل سکونت، درخواست دارم مسیر سرویس فرزندم از ابتدای ماه آینده تغییر کند.", None, "new"),
            (ago(1), "دبیرخانه مسابقات علمی دانش‌آموزی", "فراخوان مسابقه هوش مصنوعی دانش‌آموزی",
             f"مسابقه کشوری «هوش مصنوعی برای کودکان» برای دانش‌آموزان پایه‌های چهارم تا ششم برگزار می‌شود. خواهشمند است دو دانش‌آموز علاقه‌مند به همراه یک معلم راهنما را تا {jday(ahead(4))} معرفی فرمایید. اطلاع‌رسانی به اولیای دانش‌آموزان نیز توصیه می‌شود.", ahead(4), "new"),
            (ago(2), R, "اطلاعیه کارگاه آموزشی ارزشیابی توصیفی",
             f"کارگاه ارزشیابی توصیفی برای آموزگاران روز {jday(ahead(12))} برگزار می‌شود. معرفی شرکت‌کنندگان تا {jday(ahead(5))}.", ahead(5), "new"),
        ]
        if JM == 7:
            letters = letters[1:]
        for d, sender, subject, body, deadline, status in letters:
            c.execute("""INSERT INTO letters (received_date, jreceived, sender, subject, body, deadline, jdeadline, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (d.isoformat(), jstr(d), sender, subject, body,
                       deadline.isoformat() if deadline else None, jstr(deadline) if deadline else None, status))

        # Earlier monthly absence requests (every finished month of this term before last month) were answered
        # by staff, by hand. Their replies use the real numbers, so the agent can learn the reply format from them.
        y, m = to_jalali(TERM_START)[:2]
        last = (JY, JM - 1) if JM > 1 else (JY - 1, 12)
        while (y, m) < last:
            name = MONTHS[m - 1]
            sent = to_gregorian(y, m, 1) + timedelta(days=33)
            reply = stats.to_fa("با سلام و احترام\nدر پاسخ به نامه شما، " + stats.absence_text(c, m) +
                                "\nبا احترام، مدیریت دبستان جاوید")
            c.execute("""INSERT INTO letters (received_date, jreceived, sender, subject, body, deadline, jdeadline, status,
                                              category, summary, reply, handled_at)
                         VALUES (?, ?, ?, ?, ?, ?, ?, 'done', 'stats', ?, ?, 'پاسخ داده شده توسط کارمند اداری')""",
                      (sent.isoformat(), jstr(sent), R, f"درخواست آمار ماهانه غیبت دانش‌آموزان ({name}‌ماه)",
                       f"خواهشمند است آمار غیبت دانش‌آموزان در {name}‌ماه را به تفکیک پایه ارسال فرمایید.",
                       (sent + timedelta(days=3)).isoformat(), jstr(sent + timedelta(days=3)),
                       f"درخواست آمار غیبت {name}‌ماه به تفکیک پایه", reply))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)

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
        c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("INSERT INTO meta VALUES ('seeded_for', ?)", (TODAY.isoformat(),))
    print(f"school.db ready: {len(SCHOOL_DAYS)} school days, today = {jstr(TODAY)}")

if __name__ == "__main__":
    run()
