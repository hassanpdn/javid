"""The road every learner walks, and the questions of the online tests. Fixed in code: a real institute enters its
own books, prices and questions (PRODUCTION.md).

Six levels, two terms each, twelve stations in all. Both terms of a level use the same book (units 1 to 6, then 7 to
12), so a learner buys a new book only when they move up a level. A term is 20 sessions of 90 minutes, twice a week:
session 10 is the midterm and session 20 the final. The book series «English Path» is made up for the demo.

The question bank: eight multiple-choice questions per level (grammar, vocabulary, reading). The placement test
takes three of each level, easiest first. Options are stored with the right one first and shuffled once, the same way
every time (by the question's id), so the right answer is not always the first.
"""
import random

LEVELS = [   # key, CEFR, the name institutes use, in Persian, colour on screen
    ("S", "Pre-A1", "Starter", "پایه", "sky"),
    ("A1", "A1", "Elementary", "مقدماتی", "teal"),
    ("A2", "A2", "Pre-Intermediate", "پیش‌متوسط", "green"),
    ("B1", "B1", "Intermediate", "متوسط", "amber"),
    ("B2", "B2", "Upper-Intermediate", "فوق‌متوسط", "rose"),
    ("C1", "C1", "Advanced", "پیشرفته", "violet"),
]
LEVEL = {k: {"key": k, "cefr": c, "name": n, "fa": f, "hue": h} for k, c, n, f, h in LEVELS}
FEES = {"S": 3_900_000, "A1": 4_200_000, "A2": 4_500_000, "B1": 4_900_000, "B2": 5_400_000, "C1": 5_900_000}      # toman, a term
BOOK_PRICES = {"S": 620_000, "A1": 680_000, "A2": 720_000, "B1": 780_000, "B2": 820_000, "C1": 860_000}           # student's book + workbook
SESSIONS = 20
MIDTERM, FINAL = 10, 20
PASS_MARK = 70

TOPICS = {   # the twelve units of each book
    "low": ["Hello!", "Family and friends", "My day", "Food and drink", "Home", "Shopping", "Free time", "Weather and seasons",
            "Travel", "Work and jobs", "Health", "Celebrations"],
    "high": ["Identity", "Work and ambition", "Cities", "Technology", "Money", "Health and the mind", "Nature", "Media and news",
             "Learning", "Culture and art", "Science", "Our future"],
}

def _terms():
    out = []
    for k, cefr, name, fa, hue in LEVELS:
        for n in (1, 2):
            out.append({"key": f"{k}-{n}", "level": k, "num": n, "name": f"{fa} {'۱۲'[n - 1]}", "fa": f"{fa} {'۱۲'[n - 1]}", "en": f"{name} {n}", "cefr": cefr, "hue": hue,
                        "book": f"English Path {cefr}", "units": (1, 6) if n == 1 else (7, 12), "fee": FEES[k], "book_price": BOOK_PRICES[k],
                        "topics": TOPICS["low" if k in ("S", "A1", "A2") else "high"]})
    for i, t in enumerate(out):
        t["index"] = i
    return out

TERMS = _terms()
TERM = {t["key"]: t for t in TERMS}
KEYS = [t["key"] for t in TERMS]

def next_key(key):
    i = KEYS.index(key)
    return KEYS[i + 1] if i + 1 < len(KEYS) else None

def unit_of_session(n):
    """Which unit of the term (0..5) session n (1..20) teaches; None for the midterm and the final.
    Sessions 1-3 the first unit, 4-6 the second, 7-9 the third, 10 the midterm, 11-13, 14-16, 17-19, 20 the final."""
    if n in (MIDTERM, FINAL):
        return None
    return (n - 1) // 3 if n < MIDTERM else 3 + (n - 11) // 3

SKILLS = {"grammar": "دستور زبان", "vocab": "واژگان", "reading": "درک مطلب"}

# id: (level, skill, question, [right answer, wrong, wrong, wrong], passage)
_BANK = [
    ("S", "grammar", "I ___ a student.", ["am", "is", "are", "be"], None),
    ("S", "grammar", "She ___ from Iran.", ["is", "am", "are", "be"], None),
    ("S", "grammar", "There are three ___ on the table.", ["books", "book", "a book", "bookes"], None),
    ("S", "grammar", "___ is your name?", ["What", "Who", "Where", "How"], None),
    ("S", "vocab", "Monday, Tuesday, ___", ["Wednesday", "Weekend", "March", "Morning"], None),
    ("S", "vocab", "The opposite of «hot» is ___.", ["cold", "warm", "big", "old"], None),
    ("S", "vocab", "I drink ___ in the morning.", ["tea", "bread", "chairs", "pens"], None),
    ("S", "reading", "How many brothers does Sara have?", ["two", "one", "three", "twelve"],
     "Sara is twelve. She lives in Shiraz with her mother and her two brothers."),
    ("A1", "grammar", "He ___ to work every day.", ["goes", "go", "going", "is go"], None),
    ("A1", "grammar", "We ___ TV last night.", ["watched", "watch", "watches", "watching"], None),
    ("A1", "grammar", "___ you like coffee?", ["Do", "Does", "Are", "Is"], None),
    ("A1", "grammar", "There isn't ___ milk in the fridge.", ["any", "some", "a", "many"], None),
    ("A1", "vocab", "My father's sister is my ___.", ["aunt", "uncle", "cousin", "nephew"], None),
    ("A1", "vocab", "You wear a ___ on your head.", ["hat", "glove", "belt", "sock"], None),
    ("A1", "vocab", "A doctor works in a ___.", ["hospital", "bakery", "library", "garage"], None),
    ("A1", "reading", "How does Ali go to school?", ["by bus", "on foot", "by car", "by train"],
     "Ali gets up at seven. He has breakfast, and then he takes the bus to school. School starts at eight."),
    ("A2", "grammar", "I ___ in Tehran since 2019.", ["have lived", "live", "am living", "lived"], None),
    ("A2", "grammar", "This box is ___ than that one.", ["heavier", "heavy", "more heavy", "heaviest"], None),
    ("A2", "grammar", "When I arrived, they ___ dinner.", ["were having", "are having", "have", "has"], None),
    ("A2", "grammar", "You ___ wear a seatbelt. It's the law.", ["must", "can", "might", "would"], None),
    ("A2", "vocab", "I'm looking ___ my keys. Have you seen them?", ["for", "at", "after", "up"], None),
    ("A2", "vocab", "The flight was ___ because of the snow.", ["cancelled", "closed", "finished", "broken"], None),
    ("A2", "vocab", "She is very ___; she always helps other people.", ["kind", "lazy", "rude", "shy"], None),
    ("A2", "reading", "When can a family visit the museum?", ["on Saturday at 10 a.m.", "on Friday at 10 a.m.", "every day at 6 p.m.", "on Monday at 8 a.m."],
     "The museum opens at 9 a.m. and closes at 5 p.m. On Fridays it is closed. Tickets are free for children under 12."),
    ("B1", "grammar", "If I ___ more time, I would learn to play the piano.", ["had", "have", "will have", "would have"], None),
    ("B1", "grammar", "The letter ___ yesterday.", ["was sent", "sent", "has sent", "is sending"], None),
    ("B1", "grammar", "She asked me where I ___.", ["lived", "do live", "live", "am living"], None),
    ("B1", "grammar", "I'm used to ___ up early.", ["getting", "get", "got", "have got"], None),
    ("B1", "vocab", "Could you ___ me a favour?", ["do", "make", "give", "take"], None),
    ("B1", "vocab", "He finally ___ smoking last year.", ["gave up", "gave in", "gave out", "gave away"], None),
    ("B1", "vocab", "The meeting has been ___ until next week.", ["put off", "put on", "put out", "put up"], None),
    ("B1", "reading", "What problem does the text mention?", ["some home workers feel lonely", "home workers are less productive", "offices are too expensive", "colleagues talk too much"],
     "Many people believe that working from home makes them more productive. However, a third of the home workers in one company said they feel lonely and miss talking to colleagues."),
    ("B2", "grammar", "By the time we got to the cinema, the film ___.", ["had already started", "already started", "has already started", "was already starting"], None),
    ("B2", "grammar", "I wish I ___ that email; it caused so many problems.", ["hadn't sent", "didn't send", "haven't sent", "wouldn't send"], None),
    ("B2", "grammar", "___ the bad weather, the match went ahead.", ["Despite", "Although", "However", "Even though"], None),
    ("B2", "grammar", "He is thought ___ the country last week.", ["to have left", "to leave", "leaving", "having left"], None),
    ("B2", "vocab", "The company is trying to ___ costs by using less paper.", ["cut down on", "cut off", "cut out of", "cut up"], None),
    ("B2", "vocab", "The new evidence ___ doubt on his story.", ["cast", "threw out", "put down", "made"], None),
    ("B2", "vocab", "It's a ___ decision; we need to think about it carefully.", ["far-reaching", "far-fetched", "far-off", "farewell"], None),
    ("B2", "reading", "What is the critics' main point?", ["electric cars are not as clean as they seem", "electric cars are too slow", "batteries are cheap to produce", "fossil fuels are running out"],
     "Although electric cars produce no exhaust fumes, critics point out that the electricity they use is often made by burning fossil fuels, and that producing their batteries takes a great deal of energy."),
    ("C1", "grammar", "Not only ___ late, but he also forgot the documents.", ["did he arrive", "he arrived", "he did arrive", "arrived he"], None),
    ("C1", "grammar", "Had I known about the delay, I ___ a later train.", ["would have taken", "would take", "had taken", "will take"], None),
    ("C1", "grammar", "It's high time we ___ a decision.", ["made", "make", "will make", "have made"], None),
    ("C1", "grammar", "Little ___ that the party was for her.", ["did she know", "she knew", "she did know", "knew she"], None),
    ("C1", "vocab", "The minister's speech was full of ___ promises that nobody believed.", ["empty", "vacant", "blank", "bare"], None),
    ("C1", "vocab", "The scandal ___ his reputation beyond repair.", ["tarnished", "polished", "cleared", "boosted"], None),
    ("C1", "vocab", "She has a ___ for languages; she picked up Italian in a few months.", ["flair", "flare", "flavour", "fluency"], None),
    ("C1", "reading", "According to the author, how are hobbies seen today?", ["as something that should be useful", "as a waste of time", "as more important than work", "as a way to meet people"],
     "The author argues that our obsession with productivity has blurred the line between work and leisure: hobbies are now judged by what they produce rather than by the pleasure they bring."),
]

def _bank():
    out, seen = {}, {}
    for level, skill, text, options, passage in _BANK:
        seen[level] = seen.get(level, 0) + 1
        qid = f"{level}-{seen[level]}"
        order = list(range(4))
        random.Random(qid).shuffle(order)
        out[qid] = {"id": qid, "level": level, "skill": skill, "text": text, "passage": passage,
                    "options": [options[i] for i in order], "answer": order.index(0)}
    return out

QUESTIONS = _bank()
PLACEMENT = [q for lv, *_ in LEVELS for q in (f"{lv}-1", f"{lv}-5", f"{lv}-8")]   # grammar, vocabulary, reading of each level

def for_quiz(level, count, rng):
    """Questions for a class's online test: mostly its own level, a quarter from the level below."""
    keys = [k for k, *_ in LEVELS]
    own = [q for q in QUESTIONS.values() if q["level"] == level]
    i = keys.index(level)
    below = [q for q in QUESTIONS.values() if i and q["level"] == keys[i - 1]]
    n_below = min(len(below), count // 4)
    picked = rng.sample(own, min(len(own), count - n_below)) + rng.sample(below, n_below)
    return [q["id"] for q in sorted(picked, key=lambda q: (keys.index(q["level"]), q["id"]))]
