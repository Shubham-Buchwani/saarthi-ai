import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from backend.database import SessionLocal, init_db, User, Chat

def test_connection():
    print("--- Testing Database Connection (Supabase/SQLite) ---")
    try:
        # Initialise if needed
        init_db()
        db = SessionLocal()
        
        # Try a simple query
        user_count = db.query(User).count()
        chat_count = db.query(Chat).count()
        
        print(f"✅ Connection successful!")
        print(f"📊 Users in DB: {user_count}")
        print(f"📊 Chats in DB: {chat_count}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_connection()
