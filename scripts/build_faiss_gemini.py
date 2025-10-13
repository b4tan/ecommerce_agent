#!/usr/bin/env python3
# Build FAISS index using Gemini embeddings over compact product text.

import os, json, time, sqlite3
from typing import List
import numpy as np, faiss
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
load_dotenv("backend/.env")

DB_PATH   = os.getenv("DB_PATH", "./data/catalog.sqlite")
FAISS_DIR = os.getenv("FAISS_DIR", "./data/faiss")
MODEL     = os.getenv("EMBED_MODEL", "text-embedding-004")  
BATCH     = int(os.getenv("EMBED_BATCH", "64"))
MAX_DESC  = int(os.getenv("EMBED_FIELD_MAX_CHARS", "400"))

assert os.getenv("GOOGLE_API_KEY"), "Set GOOGLE_API_KEY in backend/.env"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
os.makedirs(FAISS_DIR, exist_ok=True)

TEXT_FIELDS_PREF = ["title","brand","categories","description","features","plus_content","top_review","department"]

def _connect():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    return c

def _discover_fields(conn) -> List[str]:
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(products)")}
    return [f for f in TEXT_FIELDS_PREF if f in cols]

def _compact_categories(s: str) -> str:
    parts = [p.strip() for p in s.replace("|", ">").split(">") if p.strip()]
    return " > ".join(parts[-3:]) if parts else s

def _row_text(row, fields: List[str]) -> str:
    parts = []
    for f in fields:
        v = (row[f] or "").strip()
        if not v: continue
        if f == "categories": v = _compact_categories(v)
        if f not in ("title","brand") and len(v) > MAX_DESC: v = v[:MAX_DESC].rstrip() + "…"
        parts.append(v if f == "title" else f"{f.title()}: {v}")
    return ". ".join(parts)

def _embed_batch(texts: List[str]) -> np.ndarray:
    vecs = []
    for t in texts:
        for attempt in range(3):
            try:
                r = genai.embed_content(model=MODEL, content=t)
                v = np.asarray(r["embedding"], dtype="float32")
                v /= (np.linalg.norm(v) + 1e-9)       # unit length => cosine via IP
                vecs.append(v)
                break
            except Exception:
                if attempt == 2: raise
                time.sleep(1.0 * (attempt + 1))
    return np.vstack(vecs)

def main():
    conn = _connect()
    fields = _discover_fields(conn)
    rows = conn.execute("SELECT asin, * FROM products").fetchall()
    asins = [r["asin"] for r in rows]
    texts = [_row_text(r, fields) for r in rows]

    chunks = [texts[i:i+BATCH] for i in range(0, len(texts), BATCH)]
    X = np.vstack([_embed_batch(ch) for ch in chunks]).astype("float32")

    dim = X.shape[1]
    index = faiss.IndexFlatIP(dim)    # cosine on normalized vectors
    index.add(X)

    faiss.write_index(index, os.path.join(FAISS_DIR, "index.faiss"))
    np.save(os.path.join(FAISS_DIR, "ids.npy"), np.array(asins, dtype=object))
    with open(os.path.join(FAISS_DIR, "meta.json"), "w") as f:
        json.dump({"dim": int(dim), "model": MODEL, "normalized": True, "fields": fields}, f)

    print(f"FAISS built: {index.ntotal} vectors, dim={dim}, fields={fields}")

if __name__ == "__main__":
    main()
