import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SaarthiDiagnose")

def diagnose_all():
    print("\n--- Saarthi AI System Diagnostic ---")

    print("\n[1/3] Database Connectivity...")
    try:
        from backend.database import SessionLocal, init_db, User, Chat
        init_db()
        db = SessionLocal()
        user_count = db.query(User).count()
        print(f"✅ Database connected! ({user_count} users found)")
        db.close()
    except Exception as e:
        print(f"❌ Database error: {e}")

    print("\n[2/3] Search Index (FAISS)...")
    try:
        from backend.rag.retriever import load_index
        index = load_index()
        if index:
            print(f"✅ FAISS index loaded successfully.")
        else:
            print(f"❌ FAISS index could not be loaded.")
    except Exception as e:
        print(f"❌ RAG error: {e}")

    print("\n[3/3] AI Persona (Parth/Roman Script)...")
    try:
        from backend.rag.chain import get_chain
        chain = get_chain()
        query = "Tell me one shloka for peace."
        reply, _ = chain.chat(query, "diag_session", "")

        print(f"User: {query}")
        print(f"Krishna: {reply}")

        if "Parth" in reply:
            print("✅ Addressed as Parth")
        else:
            print("❌ Did not use 'Parth'")

        import re
        non_roman = re.findall(r'[^\x00-\x7F]+', reply)
        if not non_roman:
            print("✅ All text is in Roman script")
        else:
            print(f"❌ Found non-Roman characters: {set(non_roman)}")

    except Exception as e:
        print(f"❌ AI error: {e}")

    print("\n--- Diagnostic Complete ---")

if __name__ == "__main__":
    diagnose_all()
