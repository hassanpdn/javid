"""Bad input gets a clear 4xx answer, never a crash (500)."""
import pytest
from conftest import Client, BASE
import httpx

@pytest.mark.parametrize("user,path,body,code", [
    ("edari", "/staff/letters/1/refer", {"recipients": ["user:abc"]}, 400),
    ("edari", "/staff/letters/1/refer", {"recipients": ["group:class:x"]}, 400),
    ("edari", "/staff/letters/1/refer", {"recipients": []}, 400),
    ("vali", "/parent/forms/physical", {"data": {"sleep_hours": "زیاد"}}, 400),
    ("vali", "/parent/forms/physical", {"data": {"height": 900}}, 400),
    ("vali", "/parent/forms/physical", {"data": {"vision": "عالی"}}, 400),
    ("vali", "/parent/forms/wellbeing", {"data": {"mood": "خوب"}}, 400),
    ("vali", "/parent/forms/wellbeing", {"data": {"mood": 9}}, 400),
    ("vali", "/parent/forms/unknown", {"data": {}}, 404),
    ("edari", "/staff/letters/99999/approve", {"reply": "x"}, 404),
    ("edari", "/staff/letters/99999/complete", {}, 404),
    ("modir", "/manager/warnings", {"teacher_id": 3, "text": "   "}, 400),
    ("modir", "/manager/warnings", {"teacher_id": 99999, "text": "تذکر"}, 404),
    ("modir", "/manager/letters/99999/seen", {}, 404),
    ("modir", "/manager/letters/99999/decide", {"approve": True}, 404),
    ("moshaver", "/counselor/suggestions/99999/approve", {"for_parent": "x"}, 404),
    ("moshaver", "/counselor/students/99999/notes", {"note": "x"}, 404),
    ("moshaver", "/counselor/students/1/notes", {"note": "  "}, 400),
    ("edari", "/staff/letters", {"body": "کوتاه"}, 400),
    ("edari", "/staff/letters/1/category", {"category": "nonsense"}, 400),
])
def test_bad_input(user, path, body, code):
    r = Client(user).post(path, body)
    assert r.status_code == code, f"{path} {body} -> {r.status_code} {r.text[:120]}"

def test_persian_digits_in_forms_are_accepted():
    r = Client("vali").post("/parent/forms/physical", {"data": {"height": "۱۴۰", "sleep_hours": "۹٫۵", "vision": "عادی"}})
    assert r.status_code == 200
    saved = Client("vali").get("/parent/forms/physical").json()["data"]
    assert saved["height"] == 140 and saved["sleep_hours"] == 9.5

def test_huge_question():
    r = Client("vali").post("/parent/ask", {"question": "غیبت " * 20000})
    assert r.status_code == 200

def test_html_in_letters_is_stored_as_text():
    payload = "<img src=x onerror=alert(1)>"
    r = Client("edari").post("/staff/letters", {"body": "نامه آزمون " + payload + " با متن کافی", "subject": payload})
    letter = next(l for l in Client("edari").get("/staff/letters").json() if l["id"] == r.json()["id"])
    assert letter["subject"] == payload   # Vue escapes it on screen; the browser test checks that no script runs
