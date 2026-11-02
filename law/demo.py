"""Builds a law office's open cases around today: clients, cases, the notices of each and what was done about them, for
the office in office.py. The same every time (a fixed random seed), moved to today's date.

Planted situations, each one something the panels must find by themselves:
- NEAR      the last day of an appeal is the day after tomorrow, and nothing has been done yet
- OVERDUE   the last day of a correction notice (رفع نقص) was yesterday, and no action is recorded
- HEARING   a court hearing tomorrow morning
- LATE_IN   an expert's opinion entered in the office five days after it was served: two days of its seven are left
- FRIDAY    an appeal whose twentieth day falls on a Friday, so it moves to Saturday
- IDLE      an open case with nothing done for 75 days
- LATE_DONE last month an appeal was filed two days after its last day
- NO_REPORT a client who has heard nothing about the case for 40 days
"""
import random
from datetime import date, timedelta
from . import office, store, facts

FIRST = ["علی", "مریم", "حسین", "زهرا", "رضا", "فاطمه", "محمد", "سارا", "امیر", "نرگس", "مهدی", "لیلا", "حمید", "شیما", "کاوه", "پریسا",
         "سعید", "مینا", "بهزاد", "آزاده", "فرهاد", "نسرین", "پیمان", "الناز", "مجید", "سمیرا"]
LAST = ["احمدی", "رضایی", "موسوی", "حسینی", "کریمی", "محمدی", "صادقی", "نوری", "جعفری", "اکبری", "رحیمی", "قاسمی", "یزدانی", "طاهری",
        "شریفی", "عباسی", "مرادی", "فرهادی", "کاظمی", "نجفی", "توکلی", "سلطانی", "زمانی", "بهرامی", "خسروی"]
COMPANIES = ["شرکت آریا تجارت", "شرکت ساختمانی نوین بنا", "شرکت پخش سپهر", "بانک ملت", "شرکت بیمه‌ی دانا", "شرکت فولاد البرز", "تعاونی مسکن فرهنگیان"]
TOPICS = {
    "civil": ["مطالبه‌ی وجه چک", "الزام به تنظیم سند رسمی", "فسخ قرارداد", "مطالبه‌ی خسارت تأخیر تأدیه", "تخلیه‌ی ملک استیجاری", "خلع ید"],
    "criminal": ["کلاهبرداری", "خیانت در امانت", "صدور چک بلامحل", "توهین و افترا"],
    "family": ["مطالبه‌ی مهریه", "طلاق توافقی", "حضانت فرزند", "مطالبه‌ی نفقه"],
    "enforcement": ["اجرای حکم مطالبه‌ی وجه", "توقیف اموال"],
}
COURTS = {"civil": "دادگاه عمومی حقوقی تهران", "criminal": "دادگاه کیفری دو تهران", "family": "دادگاه خانواده‌ی تهران", "enforcement": "اجرای احکام مدنی تهران"}

def _name(rnd):
    return f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"

def _phone(rnd):
    return "09" + str(rnd.choice([12, 19, 35, 36, 91, 22])) + "".join(str(rnd.randint(0, 9)) for _ in range(7))

def _number(rnd):
    return "1404" + "".join(str(rnd.randint(0, 9)) for _ in range(14))

def build():
    rnd, s = random.Random(1405), office.current()
    t = store.today()
    d = lambda n: (t + timedelta(days=n)).isoformat()
    store.init()
    store.wipe()
    with store.conn() as c:
        owner = store.add_user(c, "vakil", office.person("owner", s), "owner")
        assoc = store.add_user(c, "hamkar", office.person("associate", s), "associate")
        sec = store.add_user(c, "monshi", office.person("secretary", s), "secretary")
        store.set_meta(c, "built_for", t.isoformat())
        off = facts.holidays(c, t)
        names = {owner: office.person("owner", s), assoc: office.person("associate", s), sec: office.person("secretary", s)}
        role = {owner: "owner", assoc: "associate", sec: "secretary"}
        log = lambda day, hour, who, kind, text, cid: c.execute(
            "INSERT INTO events (at, who, role, kind, text, case_id) VALUES (?,?,?,?,?,?)",
            (f"{d(day)} {hour}", names[who], store.ROLE_NAMES[role[who]], kind, text, cid))

        def case(field, topic, who, lawyer, created, last_report, side="خواهان"):
            """A case named «topic، client», for the client who: a person's name or a company."""
            title = f"{topic}، {who}"
            client = c.execute("INSERT INTO clients (name, phone) VALUES (?,?)", (who, _phone(rnd))).lastrowid
            opponent = rnd.choice([x for x in COMPANIES if x != who]) if rnd.random() < .4 else _name(rnd)
            stage = "enforcement" if field == "enforcement" else rnd.choice(["first", "first", "appeal"])
            cid = c.execute("""INSERT INTO cases (title, client_id, opponent, side, field, court, branch, number, archive, stage, lawyer_id, status, created, last_report)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,'open',?,?)""",
                            (title, client, opponent, side, field, COURTS[field], str(rnd.randint(1, 240)), _number(rnd), str(rnd.randint(100, 999)),
                             stage, lawyer, d(created), d(last_report) if last_report is not None else None)).lastrowid
            log(created, "11:00", sec, "case", f"پرونده‌ی «{title}» باز شد", cid)
            return cid

        def notice(cid, kind, served, entered=None, status="open", done=None, who=assoc, hearing=None, note=""):
            last = moved = None
            days = facts.KINDS[kind][2]
            if days:
                last, moved = facts.deadline(d(served), days, off)
            nid = c.execute("""INSERT INTO notices (case_id, kind, served, deadline, hearing, text, status, done_at, done_by, note, entered_by, entered)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (cid, kind, d(served), last, hearing, "", status, d(done) if done is not None else None, who if done is not None else None,
                             note, sec, d(entered if entered is not None else served))).lastrowid
            log(entered if entered is not None else served, "09:30", sec, "notice", f"ابلاغیه ثبت شد: {facts.KINDS[kind][0]}", cid)
            if done is not None:
                log(done, "16:00", who, "done", f"{facts.KINDS[kind][1]} انجام شد" + (f" ({note})" if note else ""), cid)
            return nid

        # ordinary cases: past notices done in time, some deadlines more than a week away, hearings later this month
        for i in range(52):
            field = rnd.choice(["civil", "civil", "civil", "criminal", "family", "family", "enforcement"])
            cid = case(field, rnd.choice(TOPICS[field]), _name(rnd), rnd.choice([owner, assoc, assoc]), -rnd.randint(60, 400), -rnd.randint(2, 25))
            for _ in range(rnd.randint(1, 3)):
                kind = rnd.choice(["judgment", "defect", "expert", "hearing", "execution"])
                served = -rnd.randint(40, 300)
                if kind == "hearing":
                    notice(cid, kind, served, status="done", done=served + 20, hearing=f"{d(served + 20)} 10:00", note="جلسه برگزار شد")
                else:
                    notice(cid, kind, served, status="done", done=served + rnd.randint(1, 5), who=rnd.choice([owner, assoc]), note="لایحه تقدیم شد")
            if i % 4 == 0:
                notice(cid, rnd.choice(["judgment", "default"]), -rnd.randint(0, 9))   # a deadline more than a week away
            elif i % 4 == 1:
                notice(cid, "hearing", -rnd.randint(5, 30), hearing=f"{d(rnd.randint(3, 40))} {rnd.choice(['09:00', '10:30', '11:30'])}")
            log(-rnd.randint(1, 35), rnd.choice(["09:40", "12:15", "15:20", "17:05"]), rnd.choice([owner, assoc]), "note",
                rnd.choice(["پیگیری از شعبه انجام شد", "با موکل تلفنی صحبت شد", "مدارک تکمیلی از موکل گرفته شد", "پرونده در سامانه‌ی ثنا بررسی شد",
                            "لایحه‌ی دفاعیه آماده شد"]), cid)

        P = {}
        # NEAR: the appeal's last day is the day after tomorrow (found so that it does not move for a holiday)
        served = -18
        while facts.deadline(d(served), 20, off)[0] != d(2) and served > -26:
            served -= 1
        P["near"] = case("civil", "مطالبه‌ی وجه چک", "شرکت پخش سپهر", assoc, -150, -10)
        P["near_n"] = notice(P["near"], "judgment", served)
        # OVERDUE: the correction notice's last day was yesterday or the day before
        P["overdue"] = case("civil", "الزام به تنظیم سند رسمی", "کیوان رحیمی", assoc, -40, -12)
        served = -11
        while facts.deadline(d(served), 10, off)[0] >= d(0):
            served -= 1
        P["overdue_n"] = notice(P["overdue"], "defect", served)
        # HEARING tomorrow
        P["hearing"] = case("family", "مطالبه‌ی مهریه", "سیما بهرامی", owner, -120, -6, side="خواهان")
        notice(P["hearing"], "hearing", -25, hearing=f"{d(1)} 10:30")
        # LATE_IN: served six days ago, entered yesterday; seven days to object
        P["late_in"] = case("civil", "مطالبه‌ی خسارت تأخیر تأدیه", "شرکت آریا تجارت", owner, -210, -15)
        P["late_in_n"] = notice(P["late_in"], "expert", -6, entered=-1)
        # FRIDAY: the twentieth day after service is a Friday a few days from now, so the last day is Saturday
        ahead = next(k for k in range(8, 16) if (t + timedelta(days=k)).weekday() == 4)
        P["friday"] = case("civil", "فسخ قرارداد", "تعاونی مسکن فرهنگیان", assoc, -180, -9)
        P["friday_n"] = notice(P["friday"], "judgment", ahead - 20)
        # IDLE: nothing done for 75 days
        P["idle"] = case("criminal", "خیانت در امانت", "فرهاد مرادی", owner, -260, -20)
        c.execute("UPDATE events SET at = ? WHERE case_id = ?", (f"{d(-75)} 12:00", P["idle"]))
        # LATE_DONE: last month an appeal filed two days after its last day
        P["late_done"] = case("civil", "تخلیه‌ی ملک استیجاری", "لیلا کاظمی", assoc, -300, -8)
        last, _ = facts.deadline(d(-52), 20, off)
        late = (t - date.fromisoformat(last)).days
        notice(P["late_done"], "judgment", -52, status="done", done=-late + 2, who=assoc, note="دادخواست تجدیدنظر تقدیم شد")
        # NO_REPORT: a client with no news for 40 days
        P["no_report"] = case("family", "حضانت فرزند", "الناز شریفی", owner, -90, -40)
        log(-3, "10:15", owner, "note", "پیگیری از شعبه انجام شد", P["no_report"])
    return P
