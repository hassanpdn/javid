import sys
from common import normalize, embed, collection

q = normalize(" ".join(sys.argv[1:]))
r = collection().query(query_embeddings=embed([q]), n_results=3,
                       where={"access_staff": True})
for doc, meta, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
    print(f"[{meta['article']}] similarity={1-dist:.2f}  {doc[:120]}...")
