"""
Session-based conversation memory — Refactored for SQLite Persistence.
Synchronizes all chat history with the database for Saarthi AI.
"""
import logging
from sqlalchemy.orm import Session
from backend.database import Chat, Message
import datetime
import uuid

logger = logging.getLogger(__name__)

def get_or_create_chat(db_session: Session, chat_id: str, user_id: int) -> Chat:
    """Helper to ensure a chat exists in the DB before adding messages."""
    chat = db_session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        chat = Chat(
            id=chat_id,
            user_id=user_id,
            title="New Conversation",
            created_at=datetime.datetime.utcnow(),
            last_active=datetime.datetime.utcnow()
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        logger.info(f"Created new persistent chat session: {chat_id}")
    return chat

def add_message(db_session: Session, chat_id: str, role: str, content: str, user_id: int) -> None:
    """Save a message to the database for a specific chat and user."""
    chat = get_or_create_chat(db_session, chat_id, user_id)

    chat.last_active = datetime.datetime.utcnow()

    new_msg = Message(
        chat_id=chat_id,
        role=role,
        content=content,
        created_at=datetime.datetime.utcnow()
    )
    db_session.add(new_msg)
    db_session.commit()

def format_history_for_prompt(db_session: Session, chat_id: str, max_messages: int = 15) -> str:
    """Retrieve chat history from DB and format it for the LLM prompt."""
    messages = (
        db_session.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(max_messages)
        .all()
    )

    messages.reverse()

    if not messages:
        return "No prior conversation."

    lines = []
    for msg in messages:
        role_label = "User" if msg.role == "user" else "Krishna (Saarthi)"
        lines.append(f"{role_label}: {msg.content}")

    return "\n".join(lines)

def get_chat_history(db_session: Session, chat_id: str):
    """Retrieve the full history of a chat (for the UI)."""
    return (
        db_session.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )

def get_user_chats(db_session: Session, user_id: int):
    """List all past conversations for a specific user."""
    return (
        db_session.query(Chat)
        .filter(Chat.user_id == user_id)
        .order_by(Chat.last_active.desc())
        .all()
    )
