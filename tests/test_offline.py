"""The AI switch on each card (access.ai_on) and what the school assistant writes with it off (offline.py).

Off, no request may reach the model or the embedding API, every page must still answer, and every text must be built
only from real data. The end-to-end part runs a second app with the permanent account on (logins on, like the live
site); there a new assistant starts with its AI off."""
import os, subprocess, sys, tempfile, time, urllib.request
import httpx, pytest
import fake_llm, serve, checks, offline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN = {"username": "pudineh-test", "password": "admin-secret"}

# ---------- the texts, on their own ----------

CHUNKS = [
    {"text": "ماده ۱۱ - ساعات کار کارکنان اداری از ساعت ۷:۳۰ تا ۱۴ است. در روزهای پنجشنبه دفتر تا ۱۲ باز است.",
     "article": "ماده ۱۱", "short": "آیین‌نامه"},
    {"text": "ماده ۱۸ - سال مالی مدرسه از اول مهر تا پایان شهریور سال بعد است.", "article": "ماده ۱۸", "short": "آیین‌نامه"},
]

def test_document_answer_quotes_the_article_itself():
    hit = offline.best_article("ساعت کار کارکنان اداری چقدره؟", CHUNKS)
    assert hit["article"] == "ماده ۱۱" and 0 < hit["score"] <= 1
    answer = offline.answer_from(hit)
    assert answer.startswith("طبق آیین‌نامه،") and answer.endswith("(ماده ۱۱)")
    assert "۷:۳۰ تا ۱۴" in answer          # the document's own words and numbers, nothing else
    assert offline.best_article("هوای امروز بارانی است؟", CHUNKS) is None
    assert offline.best_article("چی؟", CHUNKS) is None
    assert offline.best_article("ساعت ورزش بچه‌ها در حیاط", CHUNKS) is None   # one shared word is not enough

def test_warning_names_every_late_day_with_its_time():
    alert = {"name": "نرگس کریمی", "count": 2, "dates": "۲۰ مهر ساعت ۷:۵۵، ۲۲ مهر ساعت ۸:۰۶",
             "facts": [(20, "مهر", "7:55"), (22, "مهر", "8:06")]}
    text = offline.warning(alert, "مدیر دبستان")
    assert checks.missing_dated_times(text, alert["facts"]) == [] and text.endswith("مدیر دبستان")

def test_parent_message_names_no_signal():
    f = {"first_name": "آوا", "signals": [{"type": "health", "text": "خواب کمتر"}, {"type": "grade", "text": "افت در ریاضی"}],
         "progress": [{"subject": "علوم", "now": 4, "change": 1}, {"subject": "ریاضی", "now": 2, "change": -1.5}]}
    s = offline.suggestion(f, "دبستان")
    assert "علوم" in s["for_parent"] and "خواب" not in s["for_parent"] and "ریاضی" not in s["for_parent"]
    assert not checks.unsafe_for_parent(s["for_parent"])
    assert "خواب کمتر" in s["for_counselor"]   # the counselor may read the signal

def test_letters_are_read_from_their_words():
    def cat(body):
        return offline.classify_letter({"subject": "", "body": body})["category"]
    assert cat("لطفاً وصول این بخشنامه را اعلام کنید.") == "ack"
    assert cat("آمار دانش‌آموزان هر پایه را بفرستید.") == "stats"
    assert cat("قرارداد سرویس مدرسه برای تمدید فرستاده شد.") == "decision"
    assert cat("یک نفر را برای کارگاه معرفی کنید.") == "request"
    assert cat("مدیر محترم به جلسه هماهنگی دعوت می‌شود.") == "meeting"
    got = offline.classify_letter({"subject": "", "body": "لطفاً فهرست را تا ۵ دی بفرستید. با تشکر"})
    assert got["deadline"] == "۵ دی" and got["subject"]
    menu = [{"key": "group:teachers", "label": "همه معلمان"}, {"key": "group:parents", "label": "همه اولیا"}]
    assert offline.recipients({"subject": "اطلاعیه", "body": "به اولیا اطلاع دهید."}, menu)["keys"] == ["group:parents"]

# ---------- end to end, with logins on ----------

@pytest.fixture(scope="module")
def live():
    """A second app like the live site: the permanent account on, its own data, the embedding API unreachable
    (so any embedding call shows up as an error). Returns (base url, admin client)."""
    tmp = tempfile.mkdtemp(prefix="javid-offline-")
    llm = f"http://127.0.0.1:{serve.LLM_PORT}/v1"
    env = {**os.environ, "DB_PATH": os.path.join(tmp, "school.db"), "CHROMA_PATH": os.path.join(tmp, "db"),
           "LLM_BASE_URL": llm, "EMBED_BASE_URL": llm, "LLM_API_KEY": "x", "EMBED_API_KEY": "x",
           "LLM_MODEL": "fake", "EMBED_MODEL": "fake", "DEMO_TODAY": serve.TODAY, "KEEP_DB": "1",
           "SCHOOL_PATH": os.path.join(tmp, "school.json"), "ACCESS_DB_PATH": os.path.join(tmp, "access.db"),
           "FABRIC_PATH": os.path.join(tmp, "fabric.json"), "FABRIC_DB_PATH": os.path.join(tmp, "fabric.db"),
           "FABRIC_DIR": os.path.join(tmp, "fabric_files")}
    for script in ("seed.py", "ingest.py"):
        subprocess.run([sys.executable, script], cwd=ROOT, env=env, check=True, capture_output=True)
    env.update({"ADMIN_USER": ADMIN["username"], "ADMIN_PASSWORD": ADMIN["password"], "EMBED_BASE_URL": "http://127.0.0.1:9/v1"})
    port = serve.APP_PORT + 7
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(port)], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(base + "/", timeout=1); break
        except Exception:
            time.sleep(0.2)
    admin = httpx.Client(base_url=base, timeout=30)
    assert admin.post("/access/login", json=ADMIN).status_code == 200
    assert admin.post("/setup", json=admin.get("/setup/default").json()).status_code == 200
    yield base, admin
    proc.terminate()

def as_role(admin, username):
    """The admin's browser (its access cookie) logged in to a school role."""
    token = admin.post("/login", json={"username": username, "password": "1234"}).json()["token"]
    return lambda method, path, json=None: admin.request(method, path, json=json, headers={"Authorization": f"Bearer {token}"})

def test_only_the_permanent_account_sees_and_flips_the_switch(live):
    base, admin = live
    assert admin.get("/access/status").json()["ai"] == {"school": False, "fabric": False}   # off until switched on
    p = admin.post("/access/people", json={"name": "مهمان", "username": "guest1", "password": "guest-pass",
                                           "apps": ["school"], "expires_on": None}).json()
    guest = httpx.Client(base_url=base)
    guest.post("/access/login", json={"username": "guest1", "password": "guest-pass"})
    assert guest.get("/access/status").json()["ai"] == {}            # nobody else learns whether the AI is on
    assert guest.post("/access/ai", json={"app": "school", "on": True}).status_code == 403
    admin.post(f"/access/people/{p['id']}/delete")

def test_ai_off_every_page_answers_without_the_model(live):
    base, admin = live
    fake_llm.CALLS.clear()
    manager, staff, counselor, parent = (as_role(admin, u) for u in ("modir", "edari", "moshaver", "vali"))
    assert manager("GET", "/manager/briefing").json()["text"]
    alert = next(a for a in manager("GET", "/manager/overview").json()["alerts"] if a["type"] == "teacher_late")
    draft = manager("POST", "/manager/warnings/draft", {"teacher_id": alert["teacher_id"]}).json()
    assert draft["verified"] and alert["name"] in draft["text"]
    chat = manager("POST", "/chat", {"question": "ساعت کار کارکنان اداری چقدر است؟"}).json()
    assert chat["sources"] and chat["answer"].endswith(f"({chat['sources'][0]['article']})")
    for _ in range(50):
        r = staff("POST", "/staff/agent/next")
        assert r.status_code == 200
        if r.json().get("done"):
            break
    assert counselor("GET", "/counselor/students/1/insight").json()["text"]
    assert counselor("POST", "/counselor/students/1/suggest").json()["for_parent"]
    assert parent("GET", "/parent/report").json()["text"]
    assert parent("POST", "/parent/ask", {"question": "این ماه چند روز غیبت داشته؟"}).json()["answer"]
    assert fake_llm.CALLS == []   # not one request to the model (and the embedding API is unreachable)

def test_switched_on_the_model_is_used_again(live):
    base, admin = live
    assert admin.post("/access/ai", json={"app": "school", "on": True}).json()["ai"]["school"] is True
    fake_llm.CALLS.clear()
    as_role(admin, "modir")("GET", "/manager/briefing")
    assert fake_llm.CALLS
    admin.post("/access/ai", json={"app": "school", "on": False})
