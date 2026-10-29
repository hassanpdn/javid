"""What the school assistant writes when its AI is switched off (the switch on each card, access.ai_on).

Hassan's choice: with the AI off nothing on screen changes, the texts look like the assistant's, but they are built here
by code. One rule holds: every text is made only of real data (the database's names, numbers, dates and the
documents' own sentences), so nobody is ever told anything untrue. No model and no embedding is called from here.
"""
import math, re
from jalali import MONTHS

# ---------- questions about the school's documents ----------

# Words that say nothing about the topic of a question
STOP = set("""و در به از که این آن با برای را تا یا هم اگر آیا چه چی چیه چرا چطور چگونه چقدر چقدره چند چنده چندم کی کیه کجا کدام
است هست نیست باشد بود شود می‌شود میشه شده کرد کند کنم کنیم کنند داره دارد دارند داریم باید میتونم می‌توانم میتونه
می‌تواند من ما شما او آنها اونها ها های رو هر همه یک دو سه بعد قبل الان اکنون لطفا لطفاً ممنون سلام""".split())
SUFFIXES = ("‌های", "‌ها", "های", "ها", "‌ای", "ای", "ی", "ان", "ا")   # last: the spoken plural («معلما»)

def words(text):
    """The words of a question that can be looked up: no stop words, no plural or «ی» endings."""
    out = []
    for w in re.findall(r"[\w‌]+", text.replace("؟", " ")):
        w = w.strip("‌")
        if len(w) < 2 or w in STOP or w.isdigit():
            continue
        for s in SUFFIXES:
            if w.endswith(s) and len(w) - len(s) >= 2:
                w = w[: -len(s)]
                break
        out.append(w)
    return list(dict.fromkeys(out))

# Below this share of the question's words found in one article, the answer is «not found»: a wrong article quoted
# with confidence is worse than no answer
ENOUGH = 0.6

def best_article(question, chunks):
    """The article that shares the most (and rarest) words with the question.
    chunks: [{"text", "article", "short"}]. Returns the chunk with "score" (share of the question's words found,
    0..1) and "matched" (those words), or None when no article holds enough of them."""
    ws = words(question)
    if not ws or not chunks:
        return None
    df = {w: sum(w in c["text"] for c in chunks) for w in ws}
    weight = {w: math.log(1 + len(chunks) / df[w]) for w in ws if df[w]}
    if not weight:
        return None
    def score(c):
        return sum(weight.get(w, 0) for w in ws if w in c["text"])
    top = max(chunks, key=score)
    matched = [w for w in ws if w in top["text"]]
    if len(matched) / len(ws) < ENOUGH:
        return None
    return {**top, "score": round(len(matched) / len(ws), 2), "matched": matched}

def answer_from(hit):
    """The article's own sentences that hold the question's words (at most two), then the article, like the
    model's answers end with «(ماده ۱۱)»."""
    body = re.sub(r"^ماده\s*[۰-۹\d]+\s*[-–ـ:.]?\s*", "", hit["text"].strip()).lstrip("ـ-– ")
    sentences = [s.strip() for s in re.split(r"(?<=[.!؟?])\s+|\n+", body) if len(s.strip()) > 3]
    ranked = sorted(sentences, key=lambda s: -sum(w in s for w in hit["matched"]))
    keep = [s for s in sentences if s in ranked[:2]] or sentences[:1]
    text = " ".join(keep).rstrip(" .")
    return f"طبق {hit['short']}، {text}. ({hit['article']})"

# ---------- the manager ----------

def warning(alert, signature):
    """A written warning to a late teacher: every late day with its own arrival time, from the attendance book."""
    return (f"همکار گرامی، {alert['name']}\nبا سلام و احترام\n"
            f"بر اساس دفتر حضور، شما در ۳۰ روز اخیر {alert['count']} بار پس از ساعت شروع کار به مدرسه رسیده‌اید: "
            f"{alert['dates']}.\nیادآوری می‌شود که ساعت حضور همکاران ۷:۳۰ صبح است. "
            f"خواهشمند است از این پس به این زمان توجه فرمایید.\n{signature}")

# ---------- the counselor ----------

def insight(signals):
    """Two short sentences from the signals the code found (grades, absences, health forms)."""
    texts = [s["text"] for s in signals]
    if len(texts) == 1:
        return f"در هفته‌های اخیر این نشانه دیده می‌شود: {texts[0]}. بهتر است در گفت‌وگوی بعدی با آموزگار بررسی شود."
    listed = "، ".join(texts[:-1]) + " و " + texts[-1]
    return (f"در هفته‌های اخیر چند نشانه با هم دیده می‌شود: {listed}. "
            "ممکن است این نشانه‌ها به هم ربط داشته باشند و بهتر است با هم بررسی شوند.")

def suggestion(f, school_name):
    """A step for the counselor and a message for the parent. The parent's message names no signal at all
    (no grade drop, absence or health form), only a real strength and an invitation; the counselor edits it anyway."""
    first = f["first_name"]
    strong = max(f["progress"], key=lambda p: (p["now"], p["change"]), default=None)
    topic = f["signals"][0]["text"] if f["signals"] else "روند درسی و حضور"
    for_counselor = f"گفت‌وگوی کوتاه با آموزگار {first} درباره‌ی «{topic}»، و هماهنگی یک دیدار با ولی."
    praise = f"{first} در درس {strong['subject']} کار خوبی دارد. " if strong else ""
    for_parent = (f"با سلام و احترام، ولی گرامی {first}. {praise}"
                  f"برای همراهی بیشتر با {first} در هفته‌های پیش رو، خوشحال می‌شویم در یک گفت‌وگوی کوتاه با مشاور مدرسه "
                  f"شرکت کنید. در خانه هم چند دقیقه گفت‌وگو درباره‌ی روز مدرسه‌اش می‌تواند کمک کند.\n{school_name}")
    return {"for_counselor": for_counselor, "for_parent": for_parent}

# ---------- the office's letters ----------

# Checked in this order: the first that matches decides
LETTER_RULES = [
    ("ack", r"وصول"),
    ("stats", r"آمار|تعداد|گزارش عددی"),
    ("decision", r"قرارداد|پیشنهاد|هزینه|خرید|پرداخت|تمدید"),
    ("request", r"معرفی|ارسال|فهرست|تکمیل|مهلت|اعزام"),
    ("meeting", r"جلسه|نشست|دعوت"),
    ("info", r"بخشنامه|اطلاعیه|ابلاغ|اطلاع"),
]
ACTIONS = {
    "ack": "تأیید دریافت فرستاده شود.",
    "stats": "عددهای خواسته‌شده از پایگاه داده حساب و پاسخ فرستاده شود.",
    "meeting": "زمان جلسه در تقویم مدیر ثبت شود.",
    "info": "برای اطلاع بایگانی شود.",
    "decision": "نامه برای تصمیم مدیر فرستاده شود.",
    "request": "کار خواسته‌شده تا پیش از مهلت انجام شود.",
}

def first_sentence(text, limit=140):
    s = re.split(r"(?<=[.!؟?])\s+|\n+", text.strip())[0].strip()
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"

def classify_letter(letter):
    """The same answer the model gives (category, subject, summary, action, deadline), read from the letter's words."""
    text = f"{letter['subject']} {letter['body']}"
    category = next((cat for cat, pattern in LETTER_RULES if re.search(pattern, text)), "request")
    deadline = re.search(r"([۰-۹\d]{1,2})\s*(" + "|".join(MONTHS) + ")", letter["body"])
    return {"category": category, "subject": letter["subject"] or first_sentence(letter["body"], 60),
            "summary": first_sentence(letter["body"]), "action": ACTIONS[category],
            "deadline": f"{deadline.group(1)} {deadline.group(2)}" if deadline else None}

def recipients(letter, choices):
    """Who should get a letter: the groups its words name. choices: the recipient menu (key, label, kind)."""
    text = f"{letter['subject']} {letter['body']}"
    keys = []
    if re.search(r"معلم|آموزگار|همکاران|کادر آموزشی", text):
        keys.append("group:teachers")
    if re.search(r"اولیا|والدین|خانواده", text):
        keys.append("group:parents")
    valid = {c["key"] for c in choices}
    keys = [k for k in keys if k in valid]
    reason = "متن نامه به " + " و ".join(c["label"] for c in choices if c["key"] in keys) + " اشاره کرده است." if keys else ""
    return {"keys": keys, "reason": reason}

def parent_message(letter, school_name):
    """An official letter as a short message for parents: its subject and first sentence, without the letter number."""
    body = re.sub(r"(شماره|بخشنامه شماره)\s*[:：]?\s*[\d۰-۹/\-]+", "", letter["body"])
    return f"اولیای گرامی، با سلام.\nدرباره‌ی «{letter['subject']}»: {first_sentence(body, 220)}\n{school_name}"
