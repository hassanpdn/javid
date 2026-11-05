"""The language institute's assistant: setup from nothing, the planted situations, the timetable's clashes and
moves, the roles and their privacy, the learner's road and weekly plan, online tests marked by code, the placement
test, registration and fees, and the model's numbers being checked."""
import httpx, pytest
import conftest, fake_llm

def base(path):
    return conftest.BASE + "/lang" + path

@pytest.fixture(scope="module")
def tokens():
    r = httpx.post(base("/setup"), json={"institute": httpx.get(base("/setup/default")).json()["institute"]}, timeout=120)
    assert r.status_code == 200, r.text
    out = {}
    for u in ("modir", "monshi", "ostad", "zabanamooz"):
        r = httpx.post(base("/login"), json={"username": u, "password": "1234"})
        assert r.status_code == 200, r.text
        out[u] = {"Authorization": "Bearer " + r.json()["token"]}
    return out

def get(path, who, tokens):
    return httpx.get(base(path), headers=tokens[who], timeout=30)

def post(path, body, who, tokens):
    return httpx.post(base(path), json=body, headers=tokens[who], timeout=30)

def test_every_planted_situation_once(tokens):
    o = get("/today", "modir", tokens).json()
    assert sorted(a["type"] for a in o["alerts"]) == ["absent", "capacity", "placed", "quiz", "small", "teacher", "unavailable", "unpaid", "unpaid"]
    assert o["alerts"][0]["type"] == "teacher"
    s = get("/today", "monshi", tokens).json()
    assert sorted(a["type"] for a in s["alerts"]) == ["absent", "placed", "renew", "unpaid", "unpaid"]
    t = get("/teacher/home", "ostad", tokens).json()
    assert sorted(a["type"] for a in t["alerts"]) == ["absent", "attendance", "open", "quiz"]
    assert not get("/timetable?term=current", "modir", tokens).json()["problems"]       # this term's timetable is sound

def test_curriculum_and_rules():
    from lang import curriculum as cur, facts
    assert len(cur.TERMS) == 12 and cur.next_key("B1-2") == "B2-1" and cur.next_key("C1-2") is None
    assert [cur.unit_of_session(n) for n in (1, 3, 4, 10, 11, 19, 20)] == [0, 0, 1, None, 3, 5, None]
    t = {"start": "2026-09-12"}                              # a Saturday
    assert len(facts.session_days(t, "satmon")) == len(facts.session_days(t, "wedthu")) == 20
    right = {q: cur.QUESTIONS[q]["answer"] for q in cur.PLACEMENT}
    assert facts.place(right) == "C1-2"
    a2 = {q: (a if q.split("-")[0] in ("S", "A1") else (a + 1) % 4) for q, a in right.items()}
    assert facts.place(a2) == "A2-1"
    score, skills, wrong = facts.grade(["S-1", "S-5"], {"S-1": cur.QUESTIONS["S-1"]["answer"]})
    assert score == 50 and wrong == ["S-5"] and skills == {"grammar": [1, 1], "vocab": [0, 1]}
    assert facts.money(4_900_000) == "4.9 میلیون تومان" and facts.money(620_000) == "620 هزار تومان"

def test_roles_and_privacy(tokens):
    assert httpx.get(base("/today")).status_code == 401
    assert get("/today", "ostad", tokens).status_code == 403
    assert get("/today", "zabanamooz", tokens).status_code == 403
    assert get("/students", "ostad", tokens).status_code == 403
    assert get("/brief", "monshi", tokens).status_code == 403
    tt = get("/timetable?term=current", "modir", tokens).json()["classes"]
    other = next(c for c in tt if c["teacher_id"] != 1)
    assert get(f"/classes/{other['id']}", "ostad", tokens).status_code == 403            # not her class
    mine = next(c for c in tt if c["teacher_id"] == 1)
    f = get(f"/classes/{mine['id']}", "ostad", tokens).json()
    assert all(r["phone"] == "" and r["left"] is None for r in f["roster"])            # a teacher sees no phones or fees
    assert post(f"/classes/{mine['id']}/move", {"pair": "satmon", "time": "09:00", "room": 6}, "ostad", tokens).status_code == 403

def test_fixing_the_next_terms_timetable(tokens):
    nt = get("/timetable?term=next", "modir", tokens).json()
    cap = next(p for p in nt["problems"] if p["type"] == "capacity")
    cid = cap["class_ids"][0]
    cl = next(c for c in nt["classes"] if c["id"] == cid)
    grid = get(f"/classes/{cid}/moves", "modir", tokens).json()
    from lang import facts
    tight = [g for g in grid if g["pair"] == cl["pair"] and g["time"] == cl["time"] and facts.ROOMS[g["room"]] < cl["seats"] and not g["here"]]
    assert tight and not any(g["ok"] for g in tight)
    big = next(g for g in grid if g["pair"] == cl["pair"] and g["time"] == cl["time"] and g["room"] == 4)
    assert big["ok"]
    r = post(f"/classes/{cid}/move", {"pair": cl["pair"], "time": cl["time"], "room": 4}, "modir", tokens)
    assert r.status_code == 200 and "کلاس 4" in r.json()["message"]
    clash = next(p for p in get("/timetable?term=next", "modir", tokens).json()["problems"] if p["type"] == "teacher")
    a, b = clash["class_ids"]
    taken = next(g for g in get(f"/classes/{b}/moves", "modir", tokens).json() if not g["ok"] and not g["here"])
    assert post(f"/classes/{b}/move", {"pair": taken["pair"], "time": taken["time"], "room": taken["room"]}, "modir", tokens).status_code == 409
    who = next(o for o in get(f"/classes/{b}", "modir", tokens).json()["teachers"] if o["ok"])
    assert post(f"/classes/{b}/teacher", {"teacher_id": who["id"]}, "modir", tokens).status_code == 200
    left = {p["type"] for p in get("/timetable?term=next", "modir", tokens).json()["problems"]}
    assert "capacity" not in left and "teacher" not in left and {"unavailable", "small"} <= left

def test_the_learners_road_and_plan(tokens):
    h = get("/me/home", "zabanamooz", tokens).json()
    states = [s["state"] for s in h["road"]["stations"]]
    assert states.count("current") == 1 and states.count("next") == 1 and states.index("current") == 7      # B1-2
    nx = h["road"]["next"]
    assert nx["key"] == "B2-1" and not nx["same_book"] and nx["options"] and not nx["registered"]
    kinds = {i["kind"] for i in h["plan"]["items"]}
    assert {"skill", "test"} <= kinds                                   # weak in grammar, a test open now
    item = h["plan"]["items"][0]["key"]
    assert post("/me/tick", {"item": item, "done": True}, "zabanamooz", tokens).status_code == 200
    assert next(i for i in get("/me/home", "zabanamooz", tokens).json()["plan"]["items"] if i["key"] == item)["done"]
    assert post("/me/tick", {"item": "nothing", "done": True}, "zabanamooz", tokens).status_code == 404

def test_an_online_test_marked_by_code(tokens):
    from lang import curriculum as cur
    h = get("/me/home", "zabanamooz", tokens).json()
    exam = next(e for e in h["exams"] if e["open"])
    paper = post(f"/exams/{exam['id']}/start", {}, "zabanamooz", tokens).json()
    assert all("answer" not in q for q in paper["questions"]) and paper["seconds_left"] > 0
    again = post(f"/exams/{exam['id']}/start", {}, "zabanamooz", tokens).json()
    assert again["attempt_id"] == paper["attempt_id"]                    # a reload resumes the same paper
    qs = [q["id"] for q in paper["questions"]]
    for i, q in enumerate(qs):
        choice = cur.QUESTIONS[q]["answer"] if i < len(qs) - 2 else (cur.QUESTIONS[q]["answer"] + 1) % 4
        assert post(f"/attempts/{paper['attempt_id']}/answer", {"question": q, "choice": choice}, "zabanamooz", tokens).status_code == 200
    res = post(f"/attempts/{paper['attempt_id']}/submit", {}, "zabanamooz", tokens).json()
    assert res["right"] == len(qs) - 2 and res["score"] == round(100 * (len(qs) - 2) / len(qs)) and len(res["review"]) == 2
    assert post(f"/exams/{exam['id']}/start", {}, "zabanamooz", tokens).status_code == 409
    assert post(f"/attempts/{paper['attempt_id']}/answer", {"question": qs[0], "choice": 0}, "zabanamooz", tokens).status_code == 409
    r = get(f"/exams/{exam['id']}/results", "ostad", tokens).json()
    assert any(row["name"] == "نگار صدری" for row in r["rows"]) and len(r["questions"]) == len(qs)
    assert post(f"/attempts/{paper['attempt_id']}/answer", {"question": qs[0], "choice": 0}, "monshi", tokens).status_code == 403

def test_reserving_next_term(tokens):
    nx = get("/me/home", "zabanamooz", tokens).json()["road"]["next"]
    wrong = next(c for c in get("/timetable?term=next", "modir", tokens).json()["classes"] if c["course"] != nx["key"])
    assert post("/me/reserve", {"class_id": wrong["id"]}, "zabanamooz", tokens).status_code == 409
    r = post("/me/reserve", {"class_id": nx["options"][0]["id"]}, "zabanamooz", tokens)
    assert r.status_code == 200, r.text
    assert get("/me/home", "zabanamooz", tokens).json()["road"]["next"]["registered"]
    assert post("/me/reserve", {"class_id": nx["options"][0]["id"]}, "zabanamooz", tokens).status_code == 409

def test_walk_in_placement_and_registration(tokens):
    from lang import curriculum as cur
    r = post("/students", {"name": "پرستو آزمایشی", "phone": "۰۹۱۲۷۷۷۶۶۵۵"}, "monshi", tokens)
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    assert post("/students", {"name": "تکراری", "phone": "09127776655"}, "monshi", tokens).status_code == 409
    paper = post("/placement/start", {"student_id": sid}, "monshi", tokens).json()
    for q in paper["questions"]:
        a = cur.QUESTIONS[q["id"]]["answer"]
        post(f"/attempts/{paper['attempt_id']}/answer", {"question": q["id"], "choice": a if q["level"] in ("S", "A1", "A2") else (a + 1) % 4}, "monshi", tokens)
    res = post(f"/attempts/{paper['attempt_id']}/submit", {}, "monshi", tokens).json()
    assert res["placed"] == "B1-1" and res["classes"]
    cl = next(c for c in res["classes"] if c["free"] > 0)
    e = post("/enroll", {"student_id": sid, "class_id": cl["id"]}, "monshi", tokens).json()
    assert post("/enroll", {"student_id": sid, "class_id": cl["id"]}, "monshi", tokens).status_code == 409   # one class a term
    assert post(f"/students/{sid}/payments", {"enrollment_id": e["enrollment_id"], "amount": e["fee"] + 1, "method": "card"}, "monshi", tokens).status_code == 422
    p = post(f"/students/{sid}/payments", {"enrollment_id": e["enrollment_id"], "amount": e["fee"], "method": "card"}, "monshi", tokens).json()
    assert p["left"] == 0
    road = get(f"/students/{sid}", "monshi", tokens).json()["road"]
    assert [s["state"] for s in road["stations"]][:7] == ["skipped"] * 6 + ["next"]

def test_attendance_clears_the_teachers_alert(tokens):
    a = next(x for x in get("/teacher/home", "ostad", tokens).json()["alerts"] if x["type"] == "attendance")
    sheet = get(f"/classes/{a['class_id']}/attendance?day={a['day']}", "ostad", tokens).json()
    assert not sheet["written"]
    marks = {r["student_id"]: "present" for r in sheet["rows"]}
    assert post(f"/classes/{a['class_id']}/attendance", {"day": a["day"], "marks": dict(list(marks.items())[1:])}, "ostad", tokens).status_code == 422
    assert post(f"/classes/{a['class_id']}/attendance", {"day": a["day"], "marks": marks}, "ostad", tokens).status_code == 200
    assert "attendance" not in {x["type"] for x in get("/teacher/home", "ostad", tokens).json()["alerts"]}

def test_messages_and_unpaid(tokens):
    u = next(a for a in get("/today", "monshi", tokens).json()["alerts"] if a["type"] == "unpaid")
    m = get(f"/students/{u['student_id']}/message?kind=unpaid", "monshi", tokens).json()
    assert "مانده است" in m["text"] and m["phone"].startswith("09")
    f = get(f"/students/{u['student_id']}", "monshi", tokens).json()
    e = next(x for x in f["enrollments"] if x["left"] > 0)
    post(f"/students/{u['student_id']}/payments", {"enrollment_id": e["id"], "amount": e["left"], "method": "cash"}, "monshi", tokens)
    assert u["student_id"] not in {a.get("student_id") for a in get("/today", "monshi", tokens).json()["alerts"] if a["type"] == "unpaid"}

def test_fee_message_for_next_term(tokens):
    """A learner who owes only next term's fee gets the fee message too (the file shows that balance)."""
    nx = next(c for c in get("/timetable?term=next", "modir", tokens).json()["classes"] if c["free"] > 0)
    sid = post("/students", {"name": "مهسا آزمایشی", "phone": "09127776600"}, "monshi", tokens).json()["id"]
    assert post("/enroll", {"student_id": sid, "class_id": nx["id"]}, "monshi", tokens).status_code == 200
    m = get(f"/students/{sid}/message?kind=unpaid", "monshi", tokens)
    assert m.status_code == 200 and "ترم بعد" in m.json()["text"]

def test_model_numbers_are_checked(tokens):
    fake_llm.MODE = "badnum"                                       # the model changes the numbers
    try:
        b = get("/brief", "modir", tokens).json()
        assert b["checked"] is False and "97" not in b["text"]
        n = get("/me/note", "zabanamooz", tokens).json()
        assert n["checked"] is False and "97" not in n["text"]
    finally:
        fake_llm.MODE = "good"
    a = post("/ask", {"question": "کلاس بعدی من کی است؟"}, "zabanamooz", tokens).json()
    assert a["answer"]
