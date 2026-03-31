"""
RAG Chain — Full orchestration for Saarthi AI.
Connects: user input → embedding → retrieval → prompt → LLM → response.
"""

import logging
import os
import time
from typing import Optional

import google.generativeai as genai
from google.ai import generativelanguage as glm
from groq import Groq

from backend.persona.prompts import KRISHNA_SYSTEM_PROMPT, build_rag_prompt
from backend.rag.retriever import retrieve
from backend.memory.session import format_history_for_prompt

logger = logging.getLogger(__name__)


class SaarthiChain:
    """
    The main RAG chain for Saarthi AI.
    Holds references to the LLM client and embedding client.
    """

    def __init__(self):
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not google_api_key:
            raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")

        genai.configure(api_key=google_api_key)
        self.llm_provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
        self.llm_model = os.environ.get("GEMINI_MODEL", "models/gemini-2.5-flash")
        self.embed_model = os.environ.get("EMBED_MODEL", "models/text-embedding-004")

        # Groq Setup
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.groq_client = None
        if self.llm_provider == "groq" and self.groq_api_key:
            self.groq_client = Groq(api_key=self.groq_api_key)
            logger.info(f"Groq client initialized with model: {self.groq_model}")

        # Gemini Setup (as fallback or primary)
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.75,
            top_p=0.92,
            max_output_tokens=1024,
        )

        self.model = genai.GenerativeModel(
            model_name=self.llm_model,
            system_instruction=KRISHNA_SYSTEM_PROMPT,
            generation_config=self.generation_config,
        )

        logger.info(f"SaarthiChain initialized: Provider={self.llm_provider}, LLM={self.llm_model}, Embed={self.embed_model}")

    def get_embedding(self, text: str) -> list[float]:
        # Exponential backoff for embeddings (2s, 4s, 8s)
        for attempt in range(4):
            try:
                result = genai.embed_content(
                    model=self.embed_model,
                    content=text,
                    task_type="retrieval_query",
                )
                return result["embedding"]
            except Exception as e:
                err_msg = str(e).lower()
                if ("429" in err_msg or "quota" in err_msg) and attempt < 3:
                    sleep_time = 2 ** (attempt + 1)
                    logger.warning(f"Embedding Quota hit. Retrying in {sleep_time}s... (Attempt {attempt+1})")
                    time.sleep(sleep_time)
                    continue
                raise e
        return []

    def chat(
        self,
        user_message: str,
        session_id: str,
        conversation_history: str,
    ) -> tuple[str, list[dict]]:
        """
        Main chat method. Returns (reply_text, source_chunks).
        """
        # 1. Retrieve relevant Gita teachings
        retrieved_chunks = self._retrieve_context(user_message)

        # 2. Build prompt messages
        messages = build_rag_prompt(
            user_message=user_message,
            retrieved_chunks=retrieved_chunks,
            conversation_history=conversation_history,
        )

        # 3. Generate response with Provider Logic & Exponential Backoff
        reply = ""
        
        # Scenario A: Groq (Primary for high-quota and speed)
        if self.llm_provider == "groq" and self.groq_client:
            # Convert Gemini messages to OpenAI/Groq format
            groq_messages = [
                {"role": "system", "content": KRISHNA_SYSTEM_PROMPT},
            ]
            for m in messages:
                role = m["role"]
                content = m["parts"][0]["text"]
                groq_messages.append({"role": role, "content": content})

            for attempt in range(4):
                try:
                    completion = self.groq_client.chat.completions.create(
                        messages=groq_messages,
                        model=self.groq_model,
                        temperature=0.75,
                        max_tokens=1024,
                        top_p=0.92,
                    )
                    reply = completion.choices[0].message.content.strip()
                    break
                except Exception as e:
                    err_msg = str(e).lower()
                    if ("429" in err_msg or "rate limit" in err_msg) and attempt < 3:
                        sleep_time = 3 * (2 ** attempt)
                        logger.warning(f"Groq Rate Limit. Retrying in {sleep_time}s... (Attempt {attempt+1})")
                        time.sleep(sleep_time)
                        continue
                    
                    logger.error(f"Groq generation failed after {attempt+1} attempts: {e}. Falling back to Gemini...")
                    # If Groq fails after retries, we'll try Gemini below
                    break

        # Scenario B: Gemini (Fallback or Primary)
        if not reply:
            for attempt in range(4):
                try:
                    response = self.model.generate_content(
                        contents=messages,
                    )
                    reply = response.text.strip()
                    break
                except Exception as e:
                    err_msg = str(e).lower()
                    if ("429" in err_msg or "quota" in err_msg or "500" in err_msg or "503" in err_msg) and attempt < 3:
                        sleep_time = 3 * (2 ** attempt)
                        logger.warning(f"Gemini error. Retrying in {sleep_time}s... (Attempt {attempt+1})")
                        time.sleep(sleep_time)
                        continue
                    
                    logger.error(f"Gemini generation failed: {e}")
                    reply = ("I feel the heaviness of this moment, my friend. "
                             "Something pulled me away just now — please share your thoughts again "
                             "and I will be fully present with you.")
                    break

        return reply, retrieved_chunks

    def _retrieve_context(self, query: str) -> list[dict]:
        """Retrieve relevant chunks using embedding search."""
        try:
            from backend.rag.retriever import retrieve, _metadata
            if not _metadata:
                return []

            embedding = self.get_embedding(query)

            # Use the retriever with our embedding
            from backend.rag import retriever as ret_module
            return ret_module.retrieve_with_vector(
                query_vec=embedding,
                top_k=5,
                min_score=0.25,
            )
        except Exception as e:
            logger.warning(f"Retrieval failed: {e}. Proceeding without context.")
            return []

    def get_daily_wisdom(self) -> Optional[dict]:
        """Return a random Gita teaching for the daily wisdom feature."""
        import random
        from backend.rag.retriever import _metadata
        if not _metadata:
            return None

        # Pick from action/detachment/duty themes for daily wisdom
        themes = ["duty", "action", "detachment", "equanimity", "self-knowledge"]
        theme = random.choice(themes)

        matching = [c for c in _metadata if theme in c.get("themes", [])]
        chunk = random.choice(matching) if matching else random.choice(_metadata)

        # Use the centralized DAILY_WISDOM_PROMPT from persona.prompts
        from backend.persona.prompts import DAILY_WISDOM_PROMPT
        
        prompt = f"""{DAILY_WISDOM_PROMPT}

Teaching from Chapter {chunk.get('chapter', '')}, Verses {chunk.get('verse_start', '')}–{chunk.get('verse_end', '')}:
{chunk.get('simple_summary', '')}
Core lesson: {chunk.get('core_lesson', '')}
Analogy: {chunk.get('everyday_analogy', '')}
"""

        try:
            response = self.model.generate_content(contents=prompt)
            wisdom_text = response.text.strip()
        except Exception:
            wisdom_text = chunk.get("simple_summary", "Reflect on your actions today, not their outcomes.")

        return {
            "chapter": chunk.get("chapter", 0),
            "verse_start": chunk.get("verse_start", 0),
            "verse_end": chunk.get("verse_end", 0),
            "shloka_sanskrit": chunk.get("shloka_sanskrit", ""),
            "simple_summary": chunk.get("simple_summary", ""),
            "core_lesson": chunk.get("core_lesson", ""),
            "everyday_analogy": chunk.get("everyday_analogy", ""),
            "theme": theme,
            "krishna_message": wisdom_text,
        }


# Singleton instance (initialized at startup)
_chain: Optional[SaarthiChain] = None


def get_chain() -> SaarthiChain:
    global _chain
    if _chain is None:
        _chain = SaarthiChain()
    return _chain
