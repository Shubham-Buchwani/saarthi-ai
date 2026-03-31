import json
import os
import numpy as np
import google.generativeai as genai
import faiss
from dotenv import load_dotenv
from pathlib import Path

# Fix path resolution
base_dir = Path(__file__).parent.parent
load_dotenv(base_dir / ".env")

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found.")
    exit(1)

genai.configure(api_key=api_key)

data_dir = base_dir / "data"
metadata_file = data_dir / "gita_metadata.json"
embeddings_file = data_dir / "embeddings.npy"
index_file = data_dir / "gita_index.faiss"

# 1. Load metadata
with open(metadata_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# 2. Generate embeddings
embs = []
model_name = os.environ.get("EMBED_MODEL", "models/text-embedding-004")

for chunk in data:
    text = f"{chunk.get('simple_summary', '')} {chunk.get('core_lesson', '')}"
    print(f"Embedding chunk {chunk['chunk_id']}...")
    res = genai.embed_content(
        model=model_name,
        content=text,
        task_type="retrieval_document"
    )
    embs.append(res["embedding"])

embs_arr = np.array(embs, dtype="float32")
np.save(str(embeddings_file), embs_arr)

# 3. Build FAISS index
dim = embs_arr.shape[1]
faiss.normalize_L2(embs_arr)
index = faiss.IndexFlatIP(dim)
index.add(embs_arr)
faiss.write_index(index, str(index_file))

print(f"Successfully prepared data: {len(embs)} chunks.")
