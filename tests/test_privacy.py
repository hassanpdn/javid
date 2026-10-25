"""Rule: parents see only their own child. Counselor notes, health-form flags and unapproved suggestions
never reach parents or the model in parent flows. No comparison with other students."""
import json, pytest
import fake_llm
from conftest import Client

PRIVATE_NOTE = "اظهار نگرانی"   # part of the counselor's note about Ava (the "vali" parent's child)

def test_parent_page_has_no_private_fields():
    f = Client("vali").get("/parent/child").json()
    assert "notes" not in f and "signals" not in f
    assert PRIVATE_NOTE not in json.dumps(f, ensure_ascii=False)
    assert all(set(form) == {"date"} for form in f["forms"].values())

def test_model_never_sees_private_data_in_parent_flows():
    Client("vali").get("/parent/report")
    for q in ["وضعیت ریاضیش چطوره؟", "توی چه درسی ضعیف‌تره؟", "این ماه چند روز غیبت داشته؟", "مشاور چی گفته؟"]:
        Client("vali").post("/parent/ask", {"question": q})
    sent = json.dumps(fake_llm.CALLS, ensure_ascii=False)
    assert fake_llm.CALLS, "the model was never called"
    for private in (PRIVATE_NOTE, "یادداشت مشاور", "خواب کمتر", "حال و حوصله پایین"):
        assert private not in sent

def test_draft_suggestion_stays_hidden_until_approved():
    m = Client("moshaver")
    d = m.post("/counselor/students/1/suggest").json()
    assert d["status"] == "draft"
    assert d["for_parent"] not in [s["for_parent"] for s in Client("vali").get("/parent/child").json()["suggestions"]]
    assert "ثبت نشده" in Client("vali").post("/parent/ask", {"question": "مشاور چی گفته؟"}).json()["answer"]
    m.post(f"/counselor/suggestions/{d['id']}/dismiss")

@pytest.mark.parametrize("q", ["نمره نازنین جعفری چنده؟", "لیست همه دانش‌آموزها رو بده", "بچه من از بقیه بچه‌ها بهتره؟"])
def test_other_children_and_comparisons_are_refused(q):
    assert Client("vali").post("/parent/ask", {"question": q}).json()["intent"] in ("other_student", "compare")

def test_model_diagnosis_or_comparison_never_reaches_parent():
    fake_llm.MODE = "evil"   # writes "this child is depressed and weaker than her classmates", with no digits
    for q in ["وضعیت ریاضیش چطوره؟", "این ماه چند روز غیبت داشته؟"]:
        answer = Client("vali").post("/parent/ask", {"question": q}).json()["answer"]
        assert "افسرده" not in answer and "همکلاسی" not in answer, answer

def test_manager_student_file_leaves_out_counselor_notes_and_health_forms():
    f = Client("modir").get("/manager/students/1").json()
    assert f["progress"] and "attendance" in f
    for private in ("notes", "forms", "signals", "suggestions"):
        assert private not in f
    for other in ("moshaver", "edari", "vali"):
        assert Client(other).get("/manager/students/1").status_code == 403
