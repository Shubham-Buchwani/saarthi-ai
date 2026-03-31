import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()
logging.basicConfig(level=logging.INFO)

def test_chat_insert():
    print("Testing Chat insert into Supabase...")
    try:
        from backend.database import SessionLocal, init_db, User, Chat, Message
        init_db()
        db = SessionLocal()
        
        user_count = db.query(User).count()
        print(f"Users in DB: {user_count}")
        
        chat_count = db.query(Chat).count()
        print(f"Chats in DB: {chat_count}")
        
        msg_count = db.query(Message).count()
        print(f"Messages in DB: {msg_count}")
        
        print("Database tables are healthy!")
        db.close()
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chat_insert()
