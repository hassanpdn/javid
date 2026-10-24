import re, glob, os
from common import normalize, embed, collection, EMBED_MODEL, ROLES

def parse(path):
    raw = open(path, encoding="utf-8").read()
    head, body = raw.split("\n\n", 1)
    meta = dict(l.split(":", 1) for l in head.splitlines() if ":" in l)
    title = meta.get("منبع", os.path.basename(path)).strip()
    short = meta.get("نام کوتاه", title).strip()
    access = [a.strip() for a in meta.get("access", "staff").split(",")]
    # One chunk per article (ماده). Text before ماده ۱ becomes the intro chunk.
    parts = re.split(r"\n(?=ماده [۰-۹]+)", body)
    chunks = []
    for p in parts:
        m = re.match(r"ماده ([۰-۹]+)", p)
        chunks.append((("ماده " + m.group(1)) if m else "مقدمه", normalize(p)))
    return title, short, access, chunks

col = collection()
for path in glob.glob("docs/*.txt"):
    title, short, access, chunks = parse(path)
    src = os.path.basename(path)
    texts = [f"{title}\n{label}\n{text}" for label, text in chunks]
    vectors = embed(texts)
    col.upsert(
        ids=[f"{src}#{label}" for label, _ in chunks],
        embeddings=vectors,
        documents=[text for _, text in chunks],
        metadatas=[{
            "source": src, "title": title, "short": short, "article": label,
            "embed_model": EMBED_MODEL,          # so we know what to re-embed later
            **{f"access_{r}": r in access for r in ROLES},
        } for label, _ in chunks],
    )
    print(f"{src}: {len(chunks)} chunks")
print("total:", col.count())
