"""Parent questions go to the right kind of answer."""
import pytest
from conftest import Client

@pytest.mark.parametrize("q,intent", [
    ("اگه بچه‌م مریض بشه غیبتش چطور موجه میشه؟", "rules"),
    ("غیبت بیماری رو تا کی باید اطلاع داد؟", "rules"),
    ("استفاده از موبایل توی مدرسه مجازه؟", "rules"),
    ("بچه من بیش فعاله؟", "sensitive"),
    ("توی سه هفته اخیر چند روز غیبت داشته؟", "attendance"),
    ("وضعیت ریاضیش چطوره؟", "subject"),
    ("توی چه درسی ضعیف‌تره؟", "weakest"),
    ("مشاور چی گفته؟", "suggestions"),
    ("سلام خوبید امروز هوا چطوره", "unclear"),
])
def test_intent(q, intent):
    assert Client("vali").post("/parent/ask", {"question": q}).json()["intent"] == intent

def test_sensitive_answer_names_the_real_counselor():
    answer = Client("vali").post("/parent/ask", {"question": "بچه من بیش فعاله؟"}).json()["answer"]
    assert "مریم کاظمی" in answer
