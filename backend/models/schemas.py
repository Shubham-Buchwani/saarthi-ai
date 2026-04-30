from pydantic import BaseModel, EmailStr
from typing import Optional, List
import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    username: str
    email: EmailStr
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = "auto"

class ShlokaSource(BaseModel):
    chapter: int
    verse_start: int
    verse_end: int
    source_file: str
    core_lesson: str

class ChatResponse(BaseModel):
    reply: str
    sources: List[ShlokaSource] = []
    session_id: str

class FeedbackRequest(BaseModel):
    message_id: str
    helpful: bool
    session_id: str

class DailyWisdomResponse(BaseModel):
    chapter: int
    verse_start: int
    verse_end: int
    shloka_sanskrit: str
    simple_summary: str
    core_lesson: str
    everyday_analogy: str
    theme: str

class MessageInfo(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ChatInfo(BaseModel):
    id: str
    title: str
    last_active: datetime.datetime

    class Config:
        from_attributes = True
