"""
PDF Deep-Reading & Comprehension Pipeline for Saarthi AI.

This module:
1. Extracts text from all PDFs in the data folder
2. Runs a comprehension pass (LLM summarises each chunk)
3. Generates embeddings
4. Builds the FAISS index
5. Saves metadata to JSON

Run once: python scripts/build_index.py
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────
CHUNK_SIZE = 600      # target tokens per chunk
CHUNK_OVERLAP = 100   # token overlap between chunks
DATA_DIR = Path(__file__).parent.parent / "data"


# ─────────────────────────────────────────────────────
# Step 1 — PDF Extraction
# ─────────────────────────────────────────────────────
def extract_all_pdfs(pdf_folder: Path) -> list[dict]:
    """Extract text from ALL PDFs in the given folder."""
    all_pages = []
    pdf_files = list(pdf_folder.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {pdf_folder}")
        return []
    
    logger.info(f"Found {len(pdf_files)} PDF(s): {[f.name for f in pdf_files]}")
    
    for pdf_path in pdf_files:
        logger.info(f"Extracting: {pdf_path.name}")
        try:
            doc = fitz.open(str(pdf_path))
            for i, page in enumerate(doc):
                text = page.get_text("text")
                if text.strip():
                    all_pages.append({
                        "source_file": pdf_path.name,
                        "page": i + 1,
                        "text": text,
                    })
            logger.info(f"  → Extracted {len(doc)} pages from {pdf_path.name}")
        except Exception as e:
            logger.error(f"Failed to extract {pdf_path.name}: {e}")
    
    return all_pages


# ─────────────────────────────────────────────────────
# Step 2 — Clean Text
# ─────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    """Normalize extracted PDF text."""
    text = re.sub(r'\n{3,}', '\n\n', text)          # collapse excessive newlines
    text = re.sub(r'[ \t]+', ' ', text)              # collapse whitespace
    text = re.sub(r'Page \d+\s*of\s*\d+', '', text) # remove page markers
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)  # lone numbers
    return text.strip()


# ─────────────────────────────────────────────────────
# Step 3 — Smart Chunking
# ─────────────────────────────────────────────────────
def detect_chapter_verse(text: str) -> Optional[tuple[int, int, int]]:
    """
    Try to detect chapter and verse numbers from text.
    Returns (chapter, verse_start, verse_end) or None.
    """
    # Match patterns like "Chapter 2, Verse 47" or "2.47" or "BG 2.47"
    patterns = [
        r'[Cc]hapter\s+(\d+)[,\s]+[Vv]erses?\s+(\d+)(?:\s*[-–]\s*(\d+))?',
        r'\bBG\s+(\d+)\.(\d+)(?:[-–](\d+))?',
        r'\b(\d+)\.(\d+)(?:[-–](\d+))?\b',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            ch = int(m.group(1))
            vs = int(m.group(2))
            ve = int(m.group(3)) if m.group(3) else vs
            if 1 <= ch <= 18 and 1 <= vs <= 78:
                return ch, vs, ve
    return None


def chunk_pages(pages: list[dict]) -> list[dict]:
    """
    Split pages into chunks of ~CHUNK_SIZE tokens with overlap.
    Tries to respect verse boundaries when possible.
    """
    chunks: list[dict] = []
    chunk_id: int = 0

    full_text = "\n\n".join(
        f"[PAGE {p['page']} | {p['source_file']}]\n{clean_text(p['text'])}"
        for p in pages
    )

    # Split by double newline (paragraph) first
    paragraphs = re.split(r'\n{2,}', full_text)
    
    current_chunk: str = ""
    current_source = pages[0]["source_file"] if pages else "unknown.pdf"
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Extract source file hint from page markers
        src_match = re.match(r'\[PAGE \d+ \| (.+?)\]', para)
        if src_match:
            current_source = src_match.group(1)
            para = re.sub(r'\[PAGE \d+ \| .+?\]\n?', '', para).strip()
            if not para:
                continue
        
        # Rough token estimate (1 token ≈ 4 chars)
        para_tokens = len(para) // 4
        current_tokens = len(current_chunk) // 4
        
        if current_tokens + para_tokens > CHUNK_SIZE and current_chunk:
            # Save current chunk
            chunk_info = _make_chunk(chunk_id, current_chunk, current_source)
            chunks.append(chunk_info)
            chunk_id = int(chunk_id) + 1
            
            # Start new chunk with overlap
            words = current_chunk.split()
            overlap_words = words[-CHUNK_OVERLAP:] if len(words) > CHUNK_OVERLAP else words
            current_chunk = " ".join(overlap_words) + "\n\n" + para
        else:
            current_chunk = (current_chunk + "\n\n" + para).strip()
    
    # Save last chunk
    if str(current_chunk).strip():
        chunks.append(_make_chunk(int(chunk_id), str(current_chunk), str(current_source)))
    
    logger.info(f"Created {len(chunks)} chunks from {len(pages)} pages")
    return chunks


def _make_chunk(chunk_id: int, text: str, source_file: str) -> dict:
    """Create a chunk dict with basic metadata."""
    cv = detect_chapter_verse(text)
    chapter, verse_start, verse_end = cv if cv else (0, 0, 0)
    
    return {
        "chunk_id": f"chunk_{chunk_id:04d}",
        "source_file": source_file,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "raw_text": text,
        # These will be filled by the comprehension pass:
        "shloka_sanskrit": "",
        "simple_summary": "",
        "core_lesson": "",
        "real_life_use": "",
        "everyday_analogy": "",
        "themes": [],
        "emotions": [],
    }


# ─────────────────────────────────────────────────────
# Step 4 — Comprehension Pass  (LLM)
# ─────────────────────────────────────────────────────
def run_comprehension_pass(chunks: list[dict], llm_client, model: str) -> list[dict]:
    """
    For each chunk, ask the LLM to deeply understand it.
    Fills in simple_summary, core_lesson, everyday_analogy, etc.
    """
    from backend.persona.prompts import build_comprehension_prompt
    
    enriched = []
    total = len(chunks)
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Comprehending chunk {i+1}/{total}: {chunk['chunk_id']}")
        
        verses_str = f"{chunk['verse_start']}" if chunk['verse_start'] else "unknown"
        if chunk['verse_end'] and chunk['verse_end'] != chunk['verse_start']:
            verses_str += f"–{chunk['verse_end']}"
        
        prompt = build_comprehension_prompt(
            raw_text=chunk["raw_text"][:2000],  # limit to 2k chars
            chapter=chunk["chapter"] or 0,
            verses=verses_str,
        )
        
        try:
            response = llm_client.models.generate_content(
                model=model,
                contents=prompt,
            )
            text = response.text.strip()
            
            # Clean up markdown fences if present
            text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
            text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
            
            data = json.loads(text)
            chunk.update({
                "simple_summary": data.get("simple_summary", ""),
                "core_lesson": data.get("core_lesson", ""),
                "real_life_use": data.get("real_life_use", ""),
                "everyday_analogy": data.get("everyday_analogy", ""),
                "themes": data.get("themes", []),
                "emotions": data.get("emotions", []),
            })
        except Exception as e:
            logger.warning(f"Comprehension failed for {chunk['chunk_id']}: {e}")
            # Fall back to raw text summary
            chunk["simple_summary"] = chunk["raw_text"][:300]
        
        enriched.append(chunk)
        
        # Rate limit: small delay to avoid hitting API limits
        time.sleep(0.3)
    
    return enriched


# ─────────────────────────────────────────────────────
# Step 5 — Save Metadata
# ─────────────────────────────────────────────────────
def save_metadata(chunks: list[dict], output_path: Path) -> None:
    """Save chunk metadata to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved metadata → {output_path}")
