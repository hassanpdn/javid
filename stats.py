"""Numbers the agent needs for answering statistics requests. Pure SQL, no model."""
from jalali import MONTHS

FA, EN = "۰۱۲۳۴۵۶۷۸۹", "0123456789"
def to_fa(text):
    return text.translate(str.maketrans(EN, FA))
def to_en(text):
    return text.translate(str.maketrans(FA, EN))

def absence_by_grade(c, month):
    """month: Persian month number, e.g. 9 for Azar."""
    rows = c.execute("""
        SELECT cl.grade, SUM(a.excused = 1) AS excused, SUM(a.excused = 0) AS unexcused
        FROM student_attendance a JOIN students s ON s.id = a.student_id JOIN classes cl ON cl.id = s.class_id
        WHERE a.status = 'absent' AND substr(a.jdate, 6, 2) = ? GROUP BY cl.grade ORDER BY cl.grade""",
        (f"{month:02d}",)).fetchall()
    return [{"grade": r["grade"], "excused": r["excused"], "unexcused": r["unexcused"],
             "total": r["excused"] + r["unexcused"]} for r in rows]

def students_by_grade(c):
    rows = c.execute("""SELECT cl.grade, COUNT(DISTINCT cl.id) AS classes, COUNT(s.id) AS students
                        FROM classes cl LEFT JOIN students s ON s.class_id = cl.id GROUP BY cl.grade ORDER BY cl.grade""").fetchall()
    return [dict(r) for r in rows]

GRADE_NAMES = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}

def absence_text(c, month):
    lines = [f"پایه {GRADE_NAMES[r['grade']]}: {r['total']} مورد غیبت ({r['excused']} موجه، {r['unexcused']} غیرموجه)"
             for r in absence_by_grade(c, month)]
    return f"آمار غیبت {MONTHS[month - 1]}‌ماه:\n" + "\n".join(lines)

def students_text(c):
    lines = [f"پایه {GRADE_NAMES[r['grade']]}: {r['students']} دانش‌آموز در {r['classes']} کلاس" for r in students_by_grade(c)]
    return "تعداد دانش‌آموزان به تفکیک پایه:\n" + "\n".join(lines)
