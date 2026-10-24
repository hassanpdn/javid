import os, re, json
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from common import normalize, embed, collection
from llm import ask_llm
from auth import get_token, current_user
import db
import manager
import notifications
import staff
import counselor
import parent
import parent_chat
THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.60"))
NOT_FOUND = "جواب این سؤال رو توی اسناد مدرسه پیدا نکردم. می‌تونید سؤال رو دقیق‌تر بپرسید یا با دفتر مدرسه تماس بگیرید."
UNCLEAR = "متوجه سؤالتون نشدم. لطفا سؤال رو کامل و واضح بنویسید، مثلا «ساعت کاری کارکنان اداری چقدره؟»"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

db.init()

class ChatRequest(BaseModel):
    question: str

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(req: LoginRequest):
    result = db.login(req.username.strip(), req.password)
    if not result:
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")
    token, user = result
    return {"token": token, "user": db.public_user(user)}

@app.get("/me")
def me(user: dict = Depends(current_user)):
    return db.public_user(user)

@app.post("/logout")
def logout(token: str = Depends(get_token)):
    db.logout(token)
    return {"ok": True}

def rewrite(question):
    out = ask_llm(
        "وظیفه تو فقط بازنویسی سؤال است، نه جواب دادن به آن. "
        "سؤال محاوره‌ای را به یک سؤال رسمی و کامل فارسی تبدیل کن. فقط سؤال را بنویس.\n"
        "اگر متن بی‌معنی، حروف درهم یا نامفهوم است، فقط کلمه «نامفهوم» را بنویس.\n"
        "مثال: «سیبلا یبلسی بلا» ← «نامفهوم»\n"
        "مثال: «ساعت کار چقدره» ← «ساعات کار کارکنان اداری چقدر است؟»\n"
        "مثال: «حقوق معلما چنده» ← «میزان حقوق معلمان چقدر است؟»\n"
        "مثال: «مجوز کی باطل میشه» ← «مجوز تأسیس در چه صورتی فاقد اعتبار می‌شود؟»",
        question, max_tokens=60)
    if "نامفهوم" in out:
        return None
    if not out.endswith("؟") or len(out) > len(question) * 3:
        return question
    return out

def search(queries, role):
    vectors = embed(queries)
    r = collection().query(query_embeddings=vectors, n_results=5, where={f"access_{role}": True})
    best = {}
    for ids, docs, metas, dists in zip(r["ids"], r["documents"], r["metadatas"], r["distances"]):
        for i, doc, meta, dist in zip(ids, docs, metas, dists):
            score = 1 - dist
            if i not in best or score > best[i]["score"]:
                best[i] = {"text": doc, "article": meta["article"], "short": meta.get("short", meta["title"]), "score": score}
    hits = sorted(best.values(), key=lambda h: h["score"], reverse=True)
    top_score = round(hits[0]["score"], 2) if hits else 0
    return [h for h in hits if h["score"] >= THRESHOLD and h["score"] >= hits[0]["score"] - 0.08][:3], top_score

SYSTEM = """تو دستیار پرسنل مدرسه جاوید هستی.
قوانین:
- فقط از روی «منابع» زیر جواب بده. اگر جواب در منابع نیست، بگو «این مورد در اسناد نیامده است.»
- چیزی از خودت اضافه نکن و حدس نزن.
- اگر سؤال یک پیش‌فرض اشتباه دارد که با منابع مغایر است، اول آن را صریح اصلاح کن.
  مثال: سؤال «چرا سال مالی مدرسه از فروردین است؟» ← «سال مالی مدرسه از فروردین نیست؛ از مهرماه تا پایان شهریور سال بعد است. (ماده ۱۸)»
- کوتاه، روشن و مؤدبانه به فارسی جواب بده.
- در پایان جواب، شماره ماده‌ای را که از آن استفاده کردی بنویس، مثلا «(ماده ۱۱)»."""

@app.post("/chat")
def chat(req: ChatRequest, user: dict = Depends(current_user)):
    result = answer_question(normalize(req.question), user["role"])
    db.log_chat(user, req.question, result["answer"], json.dumps(result["sources"], ensure_ascii=False))
    return result

def answer_question(q, role):
    if len(q.replace("؟", "").split()) < 2:
        return {"answer": UNCLEAR, "sources": []}
    formal = rewrite(q)
    if formal is None:
        return {"answer": UNCLEAR, "sources": []}
    hits, top_score = search([q, formal], role)
    if not hits:
        return {"answer": NOT_FOUND, "sources": [], "rewritten": formal, "top_score": top_score}
    context = "\n\n".join(f"[{h['short']} - {h['article']}]\n{h['text']}" for h in hits)
    answer = ask_llm(SYSTEM, f"منابع:\n{context}\n\nسؤال: {q}")
    cited = [h for h in hits if h["article"] in answer]
    shown = cited or hits[:1]
    return {
        "answer": answer,
        "rewritten": formal,
        "top_score": top_score,
        "sources": [{"doc": h["short"], "article": h["article"], "score": round(h["score"], 2)} for h in shown],
    }

app.include_router(manager.router)
app.include_router(notifications.router)
app.include_router(staff.router)
app.include_router(counselor.router)
app.include_router(parent.router)
app.include_router(parent_chat.router)

# Serve the built frontend (frontend/ -> npm run build -> static/) at http://localhost:8000. Must come after the API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")
