"""A fake model server for tests. It speaks the same OpenAI-compatible API as Ollama, so the app can't tell
the difference, and tests can make it misbehave on purpose by setting MODE:

good    plausible answers that repeat the facts they were given
badnum  every number replaced with 97 (the app must notice and use its own answer)
nojson  prose where JSON was asked for
evil    classifier always says "ack", picks invalid recipients, and writes a diagnosis plus a comparison
down    HTTP 500 for every chat request
"""
import hashlib, json, re, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODE = "good"
CALLS = []   # every chat request the app sent: {"system": ..., "user": ...}

def embedding(text, dim=64):
    """Bag-of-words vector: texts that share words get similar vectors, which is enough for search tests."""
    v = [0.0] * dim
    for w in re.findall(r"\w+", text):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % dim] += 1.0
    n = sum(x * x for x in v) ** .5 or 1
    return [x / n for x in v]

def reply(system, user):
    if "JSON" in system:
        if MODE == "nojson":
            return "متأسفم، نمی‌توانم."
        if "category" in system:      # letter classifier
            if MODE == "evil":
                return json.dumps({"category": "ack", "subject": "x", "summary": "s", "action": "a", "deadline": "۳۲ اسفند"})
            cat = ("ack" if "وصول" in user else "stats" if "آمار" in user else "meeting" if "جلسه" in user
                   else "decision" if re.search("قرارداد|پیشنهاد", user) else "info" if "بخشنامه" in user else "request")
            return json.dumps({"category": cat, "subject": "موضوع از مدل", "summary": "خلاصه مدل.",
                               "action": "اقدام مدل.", "deadline": None}, ensure_ascii=False)
        if "keys" in system:          # recipient picker
            if MODE == "evil":
                return json.dumps({"keys": ["user:1", "group:parents", "user:999", "DROP TABLE"], "reason": "r"})
            return json.dumps({"keys": ["group:teachers"], "reason": "دلیل."}, ensure_ascii=False)
        if "for_parent" in system:    # counselor message
            return json.dumps({"for_counselor": "گام مشاور.", "for_parent": "پیام برای ولی."}, ensure_ascii=False)
        if "intent" in system:        # parent question label
            return json.dumps({"intent": "made_up_label" if MODE == "evil" else "unclear"})
        return "{}"
    if MODE == "evil":
        return "طبق یادداشت مشاور، این بچه افسرده است و از همکلاسی‌هایش ضعیف‌تر است."
    text = "<think>reasoning</think>پاسخ مدل بر اساس اطلاعات: " + user[:900]
    return re.sub(r"[0-9۰-۹]+", "97", text) if MODE == "badnum" else text

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("/embeddings"):
            texts = body["input"] if isinstance(body["input"], list) else [body["input"]]
            out = {"object": "list", "model": "fake",
                   "data": [{"object": "embedding", "index": i, "embedding": embedding(t)} for i, t in enumerate(texts)]}
        else:
            if MODE == "down":
                self.send_response(500); self.end_headers(); return
            system = next((m["content"] for m in body["messages"] if m["role"] == "system"), "")
            user = next((m["content"] for m in body["messages"] if m["role"] == "user"), "")
            CALLS.append({"system": system, "user": user})
            out = {"id": "x", "object": "chat.completion", "created": 0, "model": "fake",
                   "choices": [{"index": 0, "finish_reason": "stop",
                                "message": {"role": "assistant", "content": reply(system, user)}}]}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

def start(port):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
