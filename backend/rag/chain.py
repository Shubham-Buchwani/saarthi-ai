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
from groq import Groq, AsyncGroq
import asyncio

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

        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.groq_client = None
        self.async_groq_client = None
        if self.llm_provider == "groq" and self.groq_api_key:
            self.groq_client = Groq(api_key=self.groq_api_key)
            self.async_groq_client = AsyncGroq(api_key=self.groq_api_key)
            logger.info(f"Groq clients (Sync/Async) initialized with model: {self.groq_model}")

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

    async def get_embedding_async(self, text: str) -> list[float]:
        for attempt in range(4):
            try:
                result = await genai.embed_content_async(
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
                    await asyncio.sleep(sleep_time)
                    continue
                raise e
        return []

    def get_embedding(self, text: str) -> list[float]:
        """Sync wrapper for embeddings."""
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.get_embedding_async(text))
        except RuntimeError:
            return asyncio.run(self.get_embedding_async(text))

    async def chat_stream(
        self,
        user_message: str,
        session_id: str,
        conversation_history: str,
        language: str = "auto",
    ):
        retrieved_chunks = await self._retrieve_context_async(user_message)

        messages = build_rag_prompt(
            user_message=user_message,
            retrieved_chunks=retrieved_chunks,
            conversation_history=conversation_history,
            language=language,
        )

        reply_full = ""
        
        if self.llm_provider == "groq" and self.async_groq_client:
            groq_messages = [
                {"role": "system", "content": KRISHNA_SYSTEM_PROMPT},
            ]
            for m in messages:
                role = m["role"]
                content = m["parts"][0]["text"]
                groq_messages.append({"role": role, "content": content})

            for attempt in range(4):
                try:
                    stream = await self.async_groq_client.chat.completions.create(
                        messages=groq_messages,
                        model=self.groq_model,
                        temperature=0.75,
                        max_tokens=1024,
                        top_p=0.92,
                        stream=True,
                    )
                    async for chunk in stream:
                        content = chunk.choices[0].delta.content or ""
                        if content:
                            reply_full += content
                            yield content
                    
                    yield {"sources": retrieved_chunks, "full_reply": reply_full}
                    return

                except Exception as e:
                    err_msg = str(e).lower()
                    if ("429" in err_msg or "rate limit" in err_msg) and attempt < 3:
                        sleep_time = 3 * (2 ** attempt)
                        await asyncio.sleep(sleep_time)
                        continue
                    logger.error(f"Groq stream failed: {e}. Falling back...")
                    break

        for attempt in range(4):
            try:
                response = await self.model.generate_content_async(
                    contents=messages,
                    stream=True,
                )
                async for chunk in response:
                    content = chunk.text
                    if content:
                        reply_full += content
                        yield content
                
                yield {"sources": retrieved_chunks, "full_reply": reply_full}
                return

            except Exception as e:
                err_msg = str(e).lower()
                if ("429" in err_msg or "quota" in err_msg) and attempt < 3:
                    sleep_time = 3 * (2 ** attempt)
                    await asyncio.sleep(sleep_time)
                    continue
                
                logger.error(f"Gemini stream failed: {e}")
                error_fallback = "I feel the path is blocked momentarily, Parth. Please speak to me again."
                yield error_fallback
                yield {"sources": [], "full_reply": error_fallback}
                break

    async def _retrieve_context_async(self, query: str) -> list[dict]:
        """Async retrieval of context."""
        try:
            from backend.rag.retriever import _metadata
            if not _metadata:
                return []

            embedding = await self.get_embedding_async(query)

            from backend.rag import retriever as ret_module
            return ret_module.retrieve_with_vector(
                query_vec=embedding,
                top_k=8,
                min_score=0.25,
            )
        except Exception as e:
            logger.warning(f"Retrieval failed: {e}. Proceeding without context.")
            return []

    def chat(
        self,
        user_message: str,
        session_id: str,
        conversation_history: str,
    ) -> tuple[str, list[dict]]:
        """Sync wrapper for tests/non-streaming usage."""
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()
        
        async def run_sync():
            full_reply = ""
            sources = []
            async for chunk in self.chat_stream(user_message, session_id, conversation_history):
                if isinstance(chunk, dict):
                    sources = chunk.get("sources", [])
                    full_reply = chunk.get("full_reply", "")
            return full_reply, sources

        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(run_sync())
        except RuntimeError:
            return asyncio.run(run_sync())

    def get_daily_wisdom(self) -> Optional[dict]:
        """Return a random Gita teaching for the daily wisdom feature."""
        import random
        from backend.rag.retriever import _metadata
        if not _metadata:
            return None

        themes = ["duty", "action", "detachment", "equanimity", "self-knowledge"]
        theme = random.choice(themes)

        matching = [c for c in _metadata if theme in c.get("themes", [])]
        chunk = random.choice(matching) if matching else random.choice(_metadata)

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


_chain: Optional[SaarthiChain] = None


def get_chain() -> SaarthiChain:
    global _chain
    if _chain is None:
        _chain = SaarthiChain()
    return _chain
