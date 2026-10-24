import json, time, urllib.request

URL = "http://localhost:8000/chat"
rows = []
for line in open("test_questions.txt", encoding="utf-8"):
    kind, q = line.strip().split("|", 1)
    body = json.dumps({"question": q}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
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
