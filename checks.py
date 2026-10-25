"""Checks on model output. The model only writes text; these functions decide whether that text may be shown.
When a check fails, the caller shows a plain answer built by code instead."""
import re

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def plain_digits(text):
    return (text or "").translate(FA_DIGITS)

def numbers(text):
    """Every whole number in the text, in order. Whole numbers only, so 13 is never mistaken for 3."""
    return re.findall(r"\d+", plain_digits(text))

def only_known_numbers(draft, facts):
    """True if every number the model wrote also appears in the facts it was given."""
    return set(numbers(draft)) <= set(numbers(facts))

def grade_lines_match(draft, data):
    """Stats replies. data has lines like 'پایه اول: 3 مورد غیبت (1 موجه، 2 غیرموجه)'.
    After each grade name the draft must have exactly that line's numbers, in the same order,
    so numbers can't be swapped between grades."""
    text = plain_digits(draft)
    for line in data.splitlines():
        m = re.match(r"(پایه \S+):", line)
        if not m:
            continue
        start = text.find(m.group(1))
        if start < 0:
            return False
        segment = text[start + len(m.group(1)):]
        nxt = segment.find("پایه ")
        segment = segment[:nxt] if nxt >= 0 else segment
        want = numbers(line)
        if numbers(segment)[:len(want)] != want:
            return False
    return True

def missing_dated_times(draft, facts):
    """Warning letters. facts: [(day, month_name, '7:55'), ...].
    Each date must appear with its own time next to it (in either order). Returns what is missing."""
    text = plain_digits(draft)
    missing = []
    for day, month, time in facts:
        date_re = rf"(?<!\d){day}\s*{month}(?:\s*\d{{4}})?"
        time_re = rf"(?<![\d:])0?{re.escape(time)}(?!\d)"
        if not (re.search(date_re + r"[^\d]{0,25}" + time_re, text) or re.search(time_re + r"[^\d]{0,25}" + date_re, text)):
            missing.append(f"{day} {month} ساعت {time}")
    return missing

def labeled_counts_ok(draft, expected):
    """Attendance answers. expected: {"غیبت": 2, "غیبت غیرموجه": 1, "تأخیر": 3}.
    A number written right before a label ('2 روز غیبت') or right after it ('تأخیر: 3')
    must be that label's count, so absences and lates can't be swapped."""
    text = plain_digits(draft).replace("تاخیر", "تأخیر")
    labels = {
        "غیبت غیرموجه": r"غیبت(?:‌?های?)?\s*غیرموجه",
        "غیبت": r"غیبت(?!(?:‌?های?)?\s*غیرموجه)",
        "تأخیر": r"تأخیر",
    }
    for name, value in expected.items():
        label = labels[name]
        before = re.findall(r"(\d+)\s*(?:روز|بار|مورد|جلسه)?\s*(?:" + label + ")", text)
        after = re.findall("(?:" + label + r")(?:‌?های?)?\s*[:：]\s*(\d+)", text)
        if any(int(n) != value for n in before + after):
            return False
    return True

# Things a text written for a parent must never contain: a diagnosis, a comparison with other children,
# or a reference to the counselor's private notes.
DIAGNOSIS = r"افسرد|اضطراب|بیش ?فعال|کم ?توجهی|اوتیس|اختلال|روان ?پریش|روانی|تشخیص|کم ?هوش|عقب ?مانده"
COMPARISON = (r"همکلاسی|مقایسه|میانگین|رتبه|نفر اول|از همه (بهتر|ضعیف|قوی)|"
              r"(بقیه|سایر|دیگر) ?(ی )?(بچه|دانش[ ‌]?آموز|شاگرد)|(بچه|دانش[ ‌]?آموز|شاگرد)(‌?ها|ان)ی? دیگر")
PRIVATE = r"یادداشت(‌?های?)? مشاور"

def unsafe_for_parent(text, other_students=()):
    """True if a parent-facing text has a diagnosis, a comparison, private notes or another student's full name."""
    if re.search(f"{DIAGNOSIS}|{COMPARISON}|{PRIVATE}", text or ""):
        return True
    return any(name in (text or "") for name in other_students)
