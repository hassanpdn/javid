"""Unit tests for checks.py: the code that decides whether model output may be shown."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import checks

def test_numbers_are_whole_numbers():
    assert checks.numbers("۱۳ و 3") == ["13", "3"]
    assert not checks.only_known_numbers("پایه اول: 13 مورد", "پایه اول: 3 مورد")

def test_grade_lines_must_keep_their_own_numbers():
    data = "آمار غیبت مهر‌ماه:\nپایه چهارم: 5 مورد غیبت (2 موجه، 3 غیرموجه)\nپایه پنجم: 7 مورد غیبت (4 موجه، 3 غیرموجه)"
    good = "در پایه چهارم ۵ مورد (۲ موجه و ۳ غیرموجه) و در پایه پنجم ۷ مورد (۴ موجه، ۳ غیرموجه) غیبت ثبت شد."
    swapped = "در پایه چهارم ۷ مورد (۴ موجه و ۳ غیرموجه) و در پایه پنجم ۵ مورد (۲ موجه، ۳ غیرموجه) غیبت ثبت شد."
    assert checks.grade_lines_match(good, data)
    assert not checks.grade_lines_match(swapped, data)
    assert not checks.grade_lines_match("فقط پایه چهارم: ۵ مورد (۲ موجه، ۳ غیرموجه)", data)

def test_each_late_date_needs_its_own_time():
    facts = [(16, "آذر", "7:55"), (23, "آذر", "8:06")]
    assert checks.missing_dated_times("تأخیرها: ۱۶ آذر ساعت ۷:۵۵ و ۲۳ آذر ساعت ۸:۰۶", facts) == []
    assert checks.missing_dated_times("تأخیرها: ۶ آذر ساعت ۷:۵۵ و ۲۳ آذر ساعت ۸:۰۶", facts) == ["16 آذر ساعت 7:55"]
    assert checks.missing_dated_times("۱۶ آذر ساعت ۸:۰۶ و ۲۳ آذر ساعت ۷:۵۵", facts) != []   # times swapped

def test_attendance_counts_stay_with_their_label():
    want = {"غیبت": 2, "غیبت غیرموجه": 1, "تأخیر": 3}
    assert checks.labeled_counts_ok("۲ روز غیبت داشته که ۱ غیبت غیرموجه بوده و ۳ بار تأخیر داشته.", want)
    assert not checks.labeled_counts_ok("۳ روز غیبت داشته و ۲ بار تأخیر.", want)

def test_parent_texts_without_diagnosis_comparison_or_other_children():
    assert checks.unsafe_for_parent("به نظر می‌رسد افسرده است")
    assert checks.unsafe_for_parent("از همکلاسی‌هایش ضعیف‌تر است")
    assert checks.unsafe_for_parent("طبق یادداشت مشاور ...")
    assert checks.unsafe_for_parent("مثل نازنین جعفری", ["نازنین جعفری"])
    assert not checks.unsafe_for_parent("ریاضی آوا نسبت به اول سال افت کرده؛ با آموزگار صحبت کنید.")
