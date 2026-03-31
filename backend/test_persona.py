import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from backend.rag.chain import get_chain

def test_persona():
    print("--- Testing Multilingual 'Parth' Persona (Roman Script) ---")
    chain = get_chain()
    
    test_queries = [
        "I am feeling lost today.",
        "Mera man bahut bhatak raha hai, kya karun?",
        "Tell me about the importance of duty in Sanskrit."
    ]
    
    for query in test_queries:
        print(f"\nUser: {query}")
        reply, _ = chain.chat(
            user_message=query,
            session_id="test_persona_session",
            conversation_history=""
        )
        print(f"Krishna: {reply}")
        
        # Basic checks
        if "Parth" in reply:
            print("✅ Addressed as Parth")
        else:
            print("❌ Did not use 'Parth'")
            
        # Check for non-Roman chars
        import re
        non_roman = re.findall(r'[^\x00-\x7F]+', reply)
        if not non_roman:
            print("✅ All text is in Roman script")
        else:
            print(f"❌ Found non-Roman characters: {set(non_roman)}")

if __name__ == "__main__":
    test_persona()
