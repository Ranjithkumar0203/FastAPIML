import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy.orm import Session

from agent import create_graph, initialize_agent
from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from database import Base, engine, get_db
from models import Message, Thread, User
from schemas import (
    ChatRequest,
    ChatResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ThreadResponse,
    TokenResponse,
)

load_dotenv()
POSTGRES_URL = os.getenv("POSTGRES_URL")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:4200").split(",")
    if origin.strip()
]

@asynccontextmanager
async def lifespan(_app: FastAPI):
    global graph
    await initialize_agent()
    async with AsyncPostgresSaver.from_conn_string(POSTGRES_URL) as checkpointer:
        await checkpointer.setup()
        graph = create_graph(checkpointer)
        yield


app = FastAPI(title="ReLU LangGraph Chat API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

graph = None


@app.get("/")
def root():
    return {"message": "LangGraph Chat API is running"}


@app.post("/auth/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


@app.post("/threads", response_model=ThreadResponse)
def create_thread(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    thread = Thread(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        title="New Chat",
        created_at=now,
        updated_at=now,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)

    return {
        "id": thread.id,
        "title": thread.title,
        "created_at": thread.created_at.isoformat(),
        "updated_at": thread.updated_at.isoformat(),
    }


@app.get("/threads", response_model=list[ThreadResponse])
def get_threads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    threads = (
        db.query(Thread)
        .filter(Thread.user_id == current_user.id)
        .order_by(Thread.updated_at.desc())
        .all()
    )

    return [
        {
            "id": thread.id,
            "title": thread.title,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
        }
        for thread in threads
    ]


@app.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
def get_messages(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = (
        db.query(Thread)
        .filter(Thread.id == thread_id, Thread.user_id == current_user.id)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = (
        db.query(Thread)
        .filter(Thread.id == request.thread_id, Thread.user_id == current_user.id)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_message = Message(
        thread_id=thread.id,
        role="user",
        content=request.message,
    )
    db.add(user_message)

    if thread.title == "New Chat":
        thread.title = request.message[:50]

    thread.updated_at = datetime.now(timezone.utc)
    db.commit()

    config = {
        "configurable": {
            "thread_id": thread.id,
            "user_id": current_user.id,
        }
    }
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": request.message}]},
        config=config,
    )

    ai_content = None
    for message in reversed(result["messages"]):
        if getattr(message, "type", None) == "ai":
            content = message.content
            ai_content = content if isinstance(content, str) else str(content)
            break

    if not ai_content:
        ai_content = "I could not generate a response."

    ai_message = Message(
        thread_id=thread.id,
        role="assistant",
        content=ai_content,
    )
    db.add(ai_message)
    thread.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"thread_id": thread.id, "message": ai_content}


@app.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = (
        db.query(Thread)
        .filter(Thread.id == thread_id, Thread.user_id == current_user.id)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    db.delete(thread)
    db.commit()
    return {"message": "Thread deleted"}
