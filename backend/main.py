"""
FastAPI main application for Saarthi AI.
Refactored for User Authentication and Persistent Chat History.
"""
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import pathlib

load_dotenv(pathlib.Path(__file__).parent / ".env")

from backend.models.schemas import (
    ChatRequest, ChatResponse, ShlokaSource,
    FeedbackRequest, DailyWisdomResponse,
    UserCreate, UserResponse, Token,
    ChatInfo, MessageInfo
)
from backend.rag.chain import get_chain
from backend.rag.retriever import load_index
from backend import database as db
from backend import auth
from backend.memory import session as session_mem
from backend.safety.filters import get_safe_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# (Imports moved down)

# ─────────────────────────────────────────────────────
# Startup / Shutdown
# ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load FAISS index and initialise database at startup."""
    logger.info("🚀 Saarthi AI starting up...")
    db.init_db()
    load_index()
    get_chain()
    logger.info("✅ Saarthi AI is ready.")
    yield
    logger.info("👋 Saarthi AI shutting down.")


app = FastAPI(
    title="Saarthi AI",
    description="Bhagavad Gita-grounded AI mentor.",
    version="2.0.0",
    lifespan=lifespan,
)

from fastapi.responses import JSONResponse
from fastapi.requests import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error connecting to wisdom source."},
    )

# CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8000",
]

# Whitelist Vercel app domains and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["https://saarthi-ai-sigma.vercel.app"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────
# AUTHENTICATION ROUTES
# ─────────────────────────────────────────────────────

@app.post("/api/auth/signup", response_model=UserResponse)
async def signup(user_in: UserCreate, db_session: Session = Depends(db.get_db)):
    """Create a new user account."""
    try:
        # Check if user exists
        db_user = db_session.query(db.User).filter(
            (db.User.username == user_in.username) | (db.User.email == user_in.email)
        ).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username or Email already registered")
        
        # Hash password and save
        hashed_pwd = auth.get_password_hash(user_in.password)
        new_user = db.User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_pwd
        )
        db_session.add(new_user)
        db_session.commit()
        db_session.refresh(new_user)
        return new_user
    except HTTPException:
        # Re-raise HTTPExceptions (like 400 'User already exists') without wrapping them in 500
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}", exc_info=True)
        # Catch and report unexpected database/logic errors as 500
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db_session: Session = Depends(db.get_db)):
    """Log in and get a JWT access token."""
    user = db_session.query(db.User).filter(db.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=UserResponse)
async def read_users_me(current_user: db.User = Depends(auth.get_current_user)):
    """Get profile of the currently logged-in user."""
    return current_user


# ─────────────────────────────────────────────────────
# CHAT & PERSISTENCE ROUTES
# ─────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest, 
    current_user: db.User = Depends(auth.get_current_user),
    db_session: Session = Depends(db.get_db)
):
    """
    Main chat endpoint (Protected).
    Saves conversation to database automatically.
    """
    # 1. Validate session/chat_id
    chat_id = req.session_id or str(uuid.uuid4())
    user_message = req.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # 2. Safety filter
    safe_response = get_safe_response(user_message)
    if safe_response:
        session_mem.add_message(db_session, chat_id, "user", user_message, current_user.id)
        session_mem.add_message(db_session, chat_id, "assistant", safe_response, current_user.id)
        return ChatResponse(reply=safe_response, sources=[], session_id=chat_id)

    # 3. Get history from DB
    history_str = session_mem.format_history_for_prompt(db_session, chat_id)

    # 4. Generate response
    try:
        chain = get_chain()
        reply, source_chunks = chain.chat(
            user_message=user_message,
            session_id=chat_id,
            conversation_history=history_str,
        )
    except Exception as e:
        logger.error(f"Chain error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Something went wrong while consulting the wise one.")

    # 5. Save to database (this guarantees get_or_create_chat has run and committed)
    session_mem.add_message(db_session, chat_id, "user", user_message, current_user.id)
    session_mem.add_message(db_session, chat_id, "assistant", reply, current_user.id)

    # 6. Handle First Message Title (Auto-naming)
    session_obj = db_session.query(db.Chat).filter(db.Chat.id == chat_id).first()
    # If title is still default, update it using the first message
    if session_obj and session_obj.title == "New Conversation":
        # simple: take first 40 chars 
        title = user_message[:40] + ("..." if len(user_message) > 40 else "")
        session_obj.title = title
        db_session.commit()

    # 7. Format sources
    sources = [
        ShlokaSource(
            chapter=c["chapter"],
            verse_start=c.get("verse_start", 0),
            verse_end=c.get("verse_end", 0),
            source_file=c.get("source_file", ""),
            core_lesson=c.get("core_lesson", "")
        ) for c in source_chunks if c.get("chapter", 0) > 0
    ]

    return ChatResponse(
        reply=reply, 
        sources=sources, 
        session_id=chat_id
    )


@app.get("/api/chats", response_model=List[ChatInfo])
async def list_chats(
    current_user: db.User = Depends(auth.get_current_user),
    db_session: Session = Depends(db.get_db)
):
    """Retrieve all conversations for the current user."""
    return session_mem.get_user_chats(db_session, current_user.id)


@app.get("/api/chats/{chat_id}", response_model=List[MessageInfo])
async def get_chat_messages(
    chat_id: str,
    current_user: db.User = Depends(auth.get_current_user),
    db_session: Session = Depends(db.get_db)
):
    """Retrieve full message history of a specific conversation."""
    messages = session_mem.get_chat_history(db_session, chat_id)
    # Security: Ensure chat belongs to current user
    chat = db_session.query(db.Chat).filter(db.Chat.id == chat_id, db.Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=403, detail="Not authorized to view this chat.")
    return messages


# ─────────────────────────────────────────────────────
# GENERAL ROUTES
# ─────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"name": "Saarthi AI", "status": "running", "version": "2.0.0"}

@app.get("/api/daily-wisdom")
async def daily_wisdom():
    chain = get_chain()
    return chain.get_daily_wisdom()
