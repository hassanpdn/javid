"""Answer-quality run for the document chat: asks every question in test_questions.txt and writes results.md.
Needs the app and the real model running. The automated tests are in tests/ (run: pytest)."""
import json, os, time, urllib.request

BASE = "http://localhost:8000"
URL = BASE + "/chat"

def login(username, password="1234"):
    req = urllib.request.Request(BASE + "/login", data=json.dumps({"username": username, "password": password}).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["token"]

# /chat answers from the documents this role may read; staff sees the administrative rules
TOKEN = login(os.getenv("TEST_USER", "edari"))
rows = []
for line in open("test_questions.txt", encoding="utf-8"):
    kind, q = line.strip().split("|", 1)
    body = json.dumps({"question": q}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
    start = time.time()
    res = json.loads(urllib.request.urlopen(req, timeout=300).read())
    secs = round(time.time() - start)
    src = "، ".join(f"{s['article']} ({s['score']})" for s in res["sources"]) or "-"
    answer = res["answer"].replace("\n", " ")
    rows.append(f"| {kind} | {q} | {res.get('rewritten', '-')} | {answer} | {src} | {res.get('top_score', '-')} | {secs} |")
    print(f"{kind}: {q} -> {secs}s")

with open("results.md", "w", encoding="utf-8") as f:
    f.write("| نوع | سؤال | بازنویسی | جواب | منبع | بهترین نمره | ثانیه |\n|---|---|---|---|---|---|---|\n")
    f.write("\n".join(rows) + "\n")
print("saved results.md")
