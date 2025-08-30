"""
dataset_gemini_25pro.py
Pipeline: dataset-only QA (math & aggregation) + Gemini 2.5 Pro polish.
Prereqs:
  pip install -U google-genai pandas sentence-transformers faiss-cpu symspellpy requests
  export GEMINI_API_KEY="your_api_key_here"
"""

import os
import json
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from symspellpy import SymSpell
from collections import deque, OrderedDict
import threading
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

# Google GenAI SDK (Gemini)
# install: pip install -U google-genai
from google import genai  # google-genai client
# or: from google import genai as genai_client

load_dotenv()

# ----------------- CONFIG -----------------
CSV_PATH = "data/database_data.csv"   # change if needed
EMBED_MODEL = "all-MiniLM-L6-v2"
EMBED_DIM = 384
TOP_K = 5
CONFIDENCE_THRESHOLD = 0.67
GEMINI_MODEL = "gemini-2.5-pro"

# read key from env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY env variable before running.")

# configure genai SDK
client = genai.Client(api_key=GEMINI_API_KEY)  # runtime config for google-genai SDK

# ------------- Spell / SymSpell --------------
sym = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

def build_symspell_from_df(df: pd.DataFrame, text_cols: List[str]):
    freq = {}
    for c in text_cols:
        for val in df[c].astype(str).fillna(""):
            for token in val.lower().split():
                freq[token] = freq.get(token, 0) + 1
    for w, cnt in freq.items():
        sym.create_dictionary_entry(w, cnt)

def correct_query(q: str) -> str:
    suggestions = sym.lookup_compound(q, max_edit_distance=2)
    if suggestions:
        return suggestions[0].term
    return q

# ------------- Vector Index (FAISS) -------------
class VectorIndex:
    def __init__(self, embed_model_name=EMBED_MODEL, dim=EMBED_DIM):
        self.model = SentenceTransformer(embed_model_name)
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.docs = []

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms==0] = 1.0
        return vectors / norms

    def add_documents(self, docs: List[Dict[str,Any]]):
        texts = [d["text"] for d in docs]
        vecs = self.model.encode(texts, convert_to_numpy=True)
        vecs = self._normalize(vecs)
        self.index.add(vecs.astype('float32'))
        self.docs.extend(docs)

    def search(self, query: str, top_k=TOP_K):
        q_vec = self.model.encode([query], convert_to_numpy=True)
        q_vec = self._normalize(q_vec)
        D, I = self.index.search(q_vec.astype('float32'), top_k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx < len(self.docs):
                results.append((float(score), self.docs[idx]))
        return results

# ------------- Simple deterministic aggregator -------------
def try_handle_aggregation(question: str, df: pd.DataFrame) -> Tuple[bool, str]:
    q = question.lower()
    import re
    m = re.search(r"(sum|total|average|avg|mean|count|max|min)\s+of\s+([\w_]+)(?:\s+where\s+(.+))?", q)
    if m:
        op, col, cond = m.groups()
        col = col.strip()
        if col not in df.columns:
            return False, ""
        subdf = df
        if cond:
            cond = cond.strip().replace("=", " = ")
            parts = cond.split()
            if len(parts) >= 2:
                ccol = parts[0]
                val = " ".join(parts[1:]).strip().strip("'\"")
                try:
                    val_cast = float(val)
                    subdf = df[df[ccol].astype(float) == val_cast]
                except:
                    subdf = df[df[ccol].astype(str) == str(val)]
        try:
            if op in ("sum", "total"):
                res = pd.to_numeric(subdf[col], errors='coerce').sum(skipna=True)
            elif op in ("average", "avg", "mean"):
                res = pd.to_numeric(subdf[col], errors='coerce').mean(skipna=True)
            elif op == "count":
                res = subdf.shape[0]
            elif op == "max":
                res = pd.to_numeric(subdf[col], errors='coerce').max(skipna=True)
            elif op == "min":
                res = pd.to_numeric(subdf[col], errors='coerce').min(skipna=True)
            else:
                return False, ""
            return True, f"{op} of {col}{' where '+cond if cond else ''}: {res}"
        except Exception:
            return False, ""
    return False, ""

# ------------- Gemini 2.5 Pro call (google-genai SDK) -------------
def call_gemini_25_pro(prompt: str, model: str = GEMINI_MODEL, max_output_tokens: int = 512) -> str:
    """
    Uses google-genai (python SDK) to call gemini-2.5-pro.
    The SDK's `client.models.generate_content` or `genai.generate_text` variants are used depending on SDK.
    This sample follows 'Client.models.generate_content' style.
    """
    # Build a request via the SDK (examples in official docs)
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=model,
        # `input` name may differ per SDK; `generate_content` accepts contents param in some versions
        contents=[
            {"type": "text", "text": prompt}
        ],
        max_output_tokens=max_output_tokens
    )
    # SDK returns structured object; convert to text safely
    # The exact path can vary; try common fields first
    if hasattr(response, "text") and response.text:
        return response.text
    # if structured with candidates
    if hasattr(response, "candidates") and response.candidates:
        return response.candidates[0].get("content", "")
    # last resort: stringify
    return str(response)

# ------------- Session Memory -------------
class SessionMemory:
    def __init__(self, max_items=50):
        self.data = {}
        self.max_items = max_items

    def add(self, sid, q, a, evidence):
        if sid not in self.data:
            self.data[sid] = deque(maxlen=self.max_items)
        self.data[sid].append({"q": q, "a": a, "evidence": evidence})

    def get(self, sid, n=5):
        if sid not in self.data: return []
        return list(self.data[sid])[-n:]

# ------------- CSV -> docs -------------
def csv_to_docs(csv_path: str):
    df = pd.read_csv(csv_path)
    docs = []
    for i, row in df.iterrows():
        summary = " | ".join([f"{c}:{row[c]}" for c in df.columns if pd.notna(row[c])])
        docs.append({"id": str(i), "text": summary, "row": row.to_dict()})
    return docs, df

# ------------- Main QA System -------------
class DatasetQASystem:
    def __init__(self, csv_path=CSV_PATH):
        self.csv_path = csv_path
        self.index = VectorIndex()
        self.df = None
        self.memory = SessionMemory()
        self.lock = threading.Lock()
        self._build_index()

    def _build_index(self):
        docs, df = csv_to_docs(self.csv_path)
        text_cols = list(df.select_dtypes(include='object').columns)
        build_symspell_from_df = globals().get("build_symspell_from_df")
        if build_symspell_from_df:
            build_symspell_from_df(df, text_cols)
        self.index.add_documents(docs)
        self.df = df

    def reload_if_changed(self):
        new_df = pd.read_csv(self.csv_path)
        if self.df is None or not new_df.equals(self.df):
            docs, _ = csv_to_docs(self.csv_path)
            self.index = VectorIndex()
            self.index.add_documents(docs)
            self.df = new_df

    def answer(self, session_id: str, raw_question: str) -> str:
        with self.lock:
            self.reload_if_changed()
        corrected = correct_query(raw_question.lower())
        handled, ans = try_handle_aggregation(corrected, self.df if self.df is not None else pd.DataFrame())
        if handled:
            self.memory.add(session_id, raw_question, ans, evidence=[])
            return ans
        results = self.index.search(corrected, top_k=TOP_K)
        if not results:
            return "I can only answer questions about the dataset. No matching data found."
        top_score, top_doc = results[0]
        if top_score < CONFIDENCE_THRESHOLD:
            return "I can only answer questions based on the dataset; I couldn't find confident evidence for your question."

        evidence_texts = [f"Score:{s:.3f} | {d['text']}" for s, d in results]
        prompt = (
            "You are a strict assistant. Use ONLY the evidence below to answer the user's question. "
            "If the answer cannot be determined from the evidence, reply exactly: 'I can only answer questions that are contained in the dataset.'\n\n"
            f"QUESTION: {raw_question}\n\nEVIDENCE:\n" + "\n".join(evidence_texts) +
            "\n\nProvide a concise numeric/text answer and any simple calculation steps you used (refer only to the evidence)."
        )

        # call Gemini 2.5 Pro
        try:
            enhanced = call_gemini_25_pro(prompt, model=GEMINI_MODEL, max_output_tokens=512)
            answer_text = enhanced
        except Exception as e:
            answer_text = "Error calling Gemini API; evidence:\n" + "\n".join(evidence_texts)

        self.memory.add(session_id, raw_question, answer_text, evidence=[d for _, d in results])
        return answer_text

# ----------------- quick test -----------------
if __name__ == "__main__":
    qa = DatasetQASystem(csv_path=CSV_PATH)
    sid = "session-1"
    while True:
        q = input("Ask dataset question (or 'exit'): ").strip()
        if q.lower() == "exit": break
        print("Thinking...")
        resp = qa.answer(sid, q)
        print("\n=== ANSWER ===\n", resp, "\n")
