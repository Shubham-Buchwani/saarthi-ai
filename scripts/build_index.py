import json
import logging
import os
import sys
import time
from pathlib import Path
import io

import numpy as np
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

env_path = Path(__file__).parent.parent / "backend" / ".env"
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY not set in .env")
        sys.exit(1)

    import google.generativeai as genai
    import fitz
    from PIL import Image
    
    genai.configure(api_key=api_key)

    embed_model = os.environ.get("EMBED_MODEL", "models/text-embedding-004")
    llm_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    data_dir = Path(__file__).parent.parent / "backend" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = data_dir / "gita_metadata.json"
    index_path = data_dir / "gita_index.faiss"
    embeddings_path = data_dir / "embeddings.npy"

    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"❌ No PDF files found in {data_dir}")
        sys.exit(1)

    pdf_path = pdf_files[0]
    logger.info(f"📖 Processing: {pdf_path.name}")
    
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    logger.info(f"  ✓ PDF has {total_pages} pages.")

    # Check if PDF has text
    has_text = any(doc[i].get_text("text").strip() for i in range(min(10, total_pages)))

    chunks = []
    
    if has_text:
        from backend.rag.ingest import extract_all_pdfs, chunk_pages
        logger.info("✂️  PDF contains text. Chunking normally...")
        pages = extract_all_pdfs(data_dir)
        raw_chunks = chunk_pages(pages)
        logger.info("🧠 Running deep comprehension pass...")
        chunks = _comprehension_pass_direct(raw_chunks, llm_model, genai)
    else:
        logger.warning("👁️  PDF appears to be an image scan. Using Gemini Vision for extraction...")
        chunks = _vision_extraction_pass(doc, pdf_path.name, llm_model, genai)

    if not chunks:
        logger.error("❌ No chunks generated. Aborting.")
        sys.exit(1)

    from backend.rag.ingest import save_metadata
    save_metadata(chunks, metadata_path)

    # ── Embeddings
    logger.info("🔢 Generating embeddings...")
    embeddings = []
    for i, chunk in enumerate(chunks):
        text_to_embed = f"{chunk.get('simple_summary', '')} {chunk.get('core_lesson', '')} {chunk.get('raw_text', '')[:500]}"
        try:
            result = genai.embed_content(
                model=embed_model,
                content=text_to_embed.strip(),
                task_type="retrieval_document",
            )
            emb = result["embedding"]
        except Exception as e:
            logger.warning(f"  Embedding failed for chunk {i}: {e}. Using zero vector.")
            emb = [0.0] * 768
        embeddings.append(emb)
        if (i + 1) % 10 == 0:
            time.sleep(0.5)

    embeddings_arr = np.array(embeddings, dtype="float32")
    np.save(str(embeddings_path), embeddings_arr)
    logger.info(f"  ✓ Embeddings saved: {embeddings_arr.shape}")

    # ── FAISS Index
    logger.info("🗂️  Building FAISS index...")
    try:
        import faiss
        dimension = embeddings_arr.shape[1]
        faiss.normalize_L2(embeddings_arr)
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings_arr)
        faiss.write_index(index, str(index_path))
        logger.info(f"  ✓ FAISS index built: {index.ntotal} vectors")
    except ImportError:
        logger.warning("  faiss-cpu not installed. Skipping FAISS.")

    logger.info("✅ Index build complete!")


def _vision_extraction_pass(doc, source_file, model_name, genai) -> list[dict]:
    import json, re, time
    from PIL import Image
    import fitz
    
    model = genai.GenerativeModel(model_name=model_name)
    chunks = []
    total = len(doc)
    
    prompt = """You are extracting wisdom from a scanned page of the Bhagavad Gita.
Analyze this image. If it contains meaningful teachings, shlokas, or commentary, extract it and return a valid JSON object.
If the page is blank, a cover page, a table of contents, or contains no actionable teachings, return exactly this JSON: {"empty": true}

Return ONLY valid JSON with these keys:
- "raw_text": The literal text/shloka extracted from the page (or a translation of it).
- "chapter": Chapter number (int), if visible. Otherwise 0.
- "verse_start": Verse number (int), if visible. Otherwise 0.
- "simple_summary": A 2-3 sentence plain-language summary for a teenager. No jargon.
- "core_lesson": The single most important life lesson in one clear sentence.
- "real_life_use": What modern real-life situation this addresses (e.g., "When you're anxious about exams").
- "everyday_analogy": A simple, visual analogy from everyday life (farming, cooking, etc).
- "themes": Array of 1-3 themes (e.g., ["duty", "action"]).
- "emotions": Array of 2-4 emotions this addresses (e.g., ["anxiety", "fear"])."""

    logger.info(f"Starting vision pass on {total} pages. This takes ~1 second per page...")
    
    for i in range(total):
        # Limit extraction to first 30 pages just so we don't hit hard rate limits and take forever
        if i >= 30:
            logger.info("  (Limiting vision extraction to first 30 pages for demonstration speed)")
            break
            
        logger.info(f"  Processing page {i+1}/{total}...")
        
        success = False
        for attempt in range(3):
            try:
                pix = doc[i].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_data = pix.tobytes("jpeg")
                img = Image.open(io.BytesIO(img_data))
                
                response = model.generate_content([prompt, img])
                text = response.text.strip()
                text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
                text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
                
                data = json.loads(text)
                if not data.get("empty"):
                    chunks.append({
                        "chunk_id": f"chunk_vis_{i:04d}",
                        "source_file": source_file,
                        "chapter": data.get("chapter", 0),
                        "verse_start": data.get("verse_start", 0),
                        "verse_end": data.get("verse_start", 0),
                        "raw_text": data.get("raw_text", ""),
                        "shloka_sanskrit": "",
                        "simple_summary": data.get("simple_summary", ""),
                        "core_lesson": data.get("core_lesson", ""),
                        "real_life_use": data.get("real_life_use", ""),
                        "everyday_analogy": data.get("everyday_analogy", ""),
                        "themes": data.get("themes", []),
                        "emotions": data.get("emotions", []),
                    })
                success = True
                break
            except Exception as e:
                logger.warning(f"  Vision extraction failed for page {i+1} (Attempt {attempt+1}): {e}")
                time.sleep(10 * (attempt + 1))
        
        if not success:
            logger.error(f"  Skipping page {i+1} after 3 failed attempts.")
            
        time.sleep(5)  # 12 requests per minute to stay under 15 RPM limit
        
    return chunks


def _comprehension_pass_direct(chunks, model_name, genai):
    import json, re, time
    from backend.persona.prompts import build_comprehension_prompt
    enriched = []
    total = len(chunks)
    model = genai.GenerativeModel(model_name=model_name)
    for i, chunk in enumerate(chunks):
        logger.info(f"  Comprehending {i+1}/{total}...")
        verses_str = str(chunk.get("verse_start", "?"))
        prompt = build_comprehension_prompt(
            raw_text=chunk["raw_text"][:2000],
            chapter=chunk.get("chapter", 0),
            verses=verses_str,
        )
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
            text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
            data = json.loads(text)
            chunk.update(data)
        except Exception as e:
            logger.warning(f"  Failed chunk {i}: {e}")
            chunk["simple_summary"] = chunk["raw_text"][:300]
        enriched.append(chunk)
        time.sleep(0.4)
    return enriched


if __name__ == "__main__":
    main()
