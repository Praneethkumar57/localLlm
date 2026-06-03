# import json
# import uuid
# import redis
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from langchain_ollama import ChatOllama
# from langchain_core.runnables.history import RunnableWithMessageHistory
# from langchain_community.chat_message_histories import RedisChatMessageHistory
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# app = FastAPI(
#     title="Local Chatbot Core Engine",
#     description="Decoupled API-first backend running LangChain and Redis state layers."
# )

# REDIS_URL = "redis://localhost:6379"

# # 1. Initialize persistent resource connections once on startup
# r_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
# llm = ChatOllama(model="llama3.2", temperature=0.3)

# # 2. Pydantic schemas for strict request/response data contracts
# class ChatPayload(BaseModel):
#     user_id: str
#     session_id: str
#     message: str

# class ChatResponsePayload(BaseModel):
#     session_id: str
#     response: str

# # 3. LangChain Engine Components
# def get_redis_history(composite_session_key: str):
#     return RedisChatMessageHistory(
#         session_id=composite_session_key,
#         url=REDIS_URL,
#         key_prefix="chat_app:",
#         ttl=604800  # Conversation histories survive for 7 days
#     )

# prompt = ChatPromptTemplate.from_messages([
#     ("system", "You are a helpful local AI assistant built using a modern decoupled architecture."),
#     MessagesPlaceholder(variable_name="chat_history"),
#     ("human", "{input}")
# ])

# chain = prompt | llm
# chain_with_redis = RunnableWithMessageHistory(
#     chain,
#     get_redis_history,
#     input_messages_key="input",
#     history_messages_key="chat_history"
# )

# # ---------------------------------------------------------
# # 4. REST API Endpoint Routes
# # ---------------------------------------------------------

# @app.get("/api/v1/sessions/{user_id}")
# async def fetch_sidebar_registry(user_id: str):
#     """Retrieves the full Hash Map index of previous chats for a specific user."""
#     metadata_key = f"chat_app:user:{user_id}:metadata"
#     try:
#         sessions = r_client.hgetall(metadata_key)
#         return {"user_id": user_id, "sessions": sessions}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Redis Hash lookup error: {str(e)}")

# @app.post("/api/v1/sessions/{user_id}/new")
# async def provision_new_session(user_id: str):
#     """Creates a fresh session token placeholder inside the user's sidebar index."""
#     metadata_key = f"chat_app:user:{user_id}:metadata"
#     new_session_id = str(uuid.uuid4())
#     r_client.hset(metadata_key, new_session_id, "New Chat Thread")
#     return {"session_id": new_session_id, "title": "New Chat Thread"}

# @app.get("/api/v1/history/{user_id}/{session_id}")
# async def get_chat_message_history(user_id: str, session_id: str):
#     """Pulls the raw JSON chat messages directly from the Redis List structure."""
#     composite_key = f"chat_app:user:{user_id}:session:{session_id}"
#     try:
#         raw_list_elements = r_client.lrange(composite_key, 0, -1)
#         # Parse the raw JSON strings into standard Python dictionaries for the client
#         parsed_history = [json.loads(element) for element in raw_list_elements]
#         return {"history": parsed_history}
#     except Exception:
#         return {"history": []}

# @app.post("/api/v1/chat", response_model=ChatResponsePayload)
# async def handle_agent_inference(payload: ChatPayload):
#     """Executes the LangChain state loop and handles smart sidebar title updating."""
#     metadata_key = f"chat_app:user:{payload.user_id}:metadata"
#     composite_session_key = f"user:{payload.user_id}:session:{payload.session_id}"
    
#     try:
#         # Dynamically auto-rename 'New Chat Thread' based on the user's first input
#         current_title = r_client.hget(metadata_key, payload.session_id)
#         if current_title == "New Chat Thread" or current_title is None:
#             short_title = payload.message[:25] + "..." if len(payload.message) > 25 else payload.message
#             r_client.hset(metadata_key, payload.session_id, short_title)

#         # Fire message context through LangChain's Redis manager wrapper
#         config = {"configurable": {"session_id": composite_session_key}}
#         result = chain_with_redis.invoke({"input": payload.message}, config=config)
        
#         return ChatResponsePayload(session_id=payload.session_id, response=result.content)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Agent inference exception: {str(e)}")




"""
backend.py  –  FastAPI core engine
Features: JWT auth, per-user PDF RAG, streaming SSE responses, Redis session store
Run with: uvicorn backend:app --reload --port 8000
"""

"""
backend.py  –  FastAPI core engine
Features: JWT auth, per-user PDF RAG, streaming SSE responses, Redis session store
Run with: uvicorn backend:app --reload --port 8000
"""

"""
backend.py  –  FastAPI core engine
Features: JWT auth, per-user PDF RAG, streaming SSE responses, Redis session store
Run with: uvicorn backend:app --reload --port 8000
"""

import json
import uuid
import hashlib
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional

import redis
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext

from langchain_ollama import ChatOllama
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage

# PDF / RAG imports
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings


# ─────────────────────────────────────────────
# Config & Constants
# ─────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-local-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

REDIS_URL = "redis://localhost:6379"
UPLOAD_DIR = "./uploads"
VECTOR_DIR = "./vectorstores"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# App Init
# ─────────────────────────────────────────────
app = FastAPI(
    title="Local Chatbot Core Engine",
    description="API-first backend: JWT auth + LangChain + Redis + FAISS RAG + SSE Streaming"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

r_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

@app.on_event("startup")
async def check_redis():
    try:
        r_client.ping()
        print("✅ Redis connected successfully")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Start Redis with:  docker run -d -p 6379:6379 redis:alpine")
        raise RuntimeError(f"Cannot connect to Redis at {REDIS_URL}") from e
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

llm = ChatOllama(model="llama3.2", temperature=0.3)
embeddings = OllamaEmbeddings(model="nomic-embed-text-v2-moe")

# ─────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────
class RegisterPayload(BaseModel):
    username: str
    password: str

class LoginPayload(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

class ChatPayload(BaseModel):
    session_id: str
    message: str
    use_rag: bool = False   # if True, answer from uploaded PDF context

class NewSessionResponse(BaseModel):
    session_id: str
    title: str

# ─────────────────────────────────────────────
# Auth Helpers
# ─────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Decode JWT and return username, raise 401 on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# ─────────────────────────────────────────────
# LangChain Chain Setup
# ─────────────────────────────────────────────
def get_redis_history(composite_session_key: str) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(
        session_id=composite_session_key,
        url=REDIS_URL,
        key_prefix="chat_app:",
        ttl=604800  # 7 days
    )

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful local AI assistant. Be concise and clear in your responses."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

chain = prompt | llm
chain_with_history = RunnableWithMessageHistory(
    chain,
    get_redis_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)

# ─────────────────────────────────────────────
# RAG Helpers
# ─────────────────────────────────────────────
def get_vectorstore_path(username: str) -> str:
    return os.path.join(VECTOR_DIR, username)

def load_vectorstore(username: str) -> Optional[FAISS]:
    path = get_vectorstore_path(username)
    if os.path.exists(path):
        return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    return None

def build_vectorstore(username: str, text: str) -> FAISS:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)
    vs = FAISS.from_texts(chunks, embeddings)
    vs.save_local(get_vectorstore_path(username))
    return vs

# ─────────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────────
@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(payload: RegisterPayload):
    username = payload.username.strip().lower()
    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user_key = f"chat_app:users:{username}"
    if r_client.exists(user_key):
        raise HTTPException(status_code=409, detail="Username already taken")

    hashed = hash_password(payload.password)
    r_client.hset(user_key, mapping={"username": username, "password_hash": hashed})

    token = create_access_token({"sub": username})
    return TokenResponse(access_token=token, username=username)


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(payload: LoginPayload):
    username = payload.username.strip().lower()
    user_key = f"chat_app:users:{username}"

    user_data = r_client.hgetall(user_key)
    if not user_data:
        raise HTTPException(status_code=401, detail="User not found")

    if not verify_password(payload.password, user_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    token = create_access_token({"sub": username})
    return TokenResponse(access_token=token, username=username)


# ─────────────────────────────────────────────
# Session Routes (protected)
# ─────────────────────────────────────────────
@app.get("/api/v1/sessions")
async def list_sessions(current_user: str = Depends(get_current_user)):
    metadata_key = f"chat_app:user:{current_user}:metadata"
    sessions = r_client.hgetall(metadata_key)
    return {"username": current_user, "sessions": sessions}


@app.post("/api/v1/sessions/new", response_model=NewSessionResponse)
async def new_session(current_user: str = Depends(get_current_user)):
    metadata_key = f"chat_app:user:{current_user}:metadata"
    session_id = str(uuid.uuid4())
    r_client.hset(metadata_key, session_id, "New Chat")
    return NewSessionResponse(session_id=session_id, title="New Chat")


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str, current_user: str = Depends(get_current_user)):
    metadata_key = f"chat_app:user:{current_user}:metadata"
    r_client.hdel(metadata_key, session_id)
    # also wipe the redis history
    history_key = f"chat_app:user:{current_user}:session:{session_id}"
    r_client.delete(history_key)
    return {"deleted": session_id}


# ─────────────────────────────────────────────
# Chat History Route
# ─────────────────────────────────────────────
@app.get("/api/v1/history/{session_id}")
async def get_history(session_id: str, current_user: str = Depends(get_current_user)):
    composite_key = f"chat_app:user:{current_user}:session:{session_id}"
    try:
        raw = r_client.lrange(composite_key, 0, -1)
        parsed = [json.loads(el) for el in reversed(raw)]
    except Exception:
        parsed = []
    return {"history": parsed}


# ─────────────────────────────────────────────
# PDF Upload Route
# ─────────────────────────────────────────────
@app.post("/api/v1/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Save the file
    save_path = os.path.join(UPLOAD_DIR, f"{current_user}_{file.filename}")
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    reader = PdfReader(save_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        raise HTTPException(status_code=422, detail="PDF has no extractable text (scanned?)")

    # Build / update vectorstore for this user
    build_vectorstore(current_user, text)

    # Track filename in Redis
    r_client.hset(f"chat_app:user:{current_user}:pdfs", file.filename, save_path)

    return {"message": f"PDF '{file.filename}' indexed successfully", "pages": len(reader.pages)}


@app.get("/api/v1/pdfs")
async def list_pdfs(current_user: str = Depends(get_current_user)):
    pdfs = r_client.hkeys(f"chat_app:user:{current_user}:pdfs")
    has_vectorstore = os.path.exists(get_vectorstore_path(current_user))
    return {"pdfs": pdfs, "rag_ready": has_vectorstore}


# ─────────────────────────────────────────────
# Streaming Chat Route
# ─────────────────────────────────────────────
@app.post("/api/v1/chat/stream")
async def stream_chat(payload: ChatPayload, current_user: str = Depends(get_current_user)):
    """
    SSE streaming endpoint. Yields chunks as they arrive from the LLM.
    Each chunk is a plain-text data frame; frontend reads via requests iter_lines().
    """
    metadata_key = f"chat_app:user:{current_user}:metadata"
    composite_session_key = f"user:{current_user}:session:{payload.session_id}"

    # Auto-rename "New Chat" title on first message
    current_title = r_client.hget(metadata_key, payload.session_id)
    if current_title in ("New Chat", None):
        short_title = payload.message[:28] + "…" if len(payload.message) > 28 else payload.message
        r_client.hset(metadata_key, payload.session_id, short_title)

    async def event_generator():
        full_response = []

        if payload.use_rag:
            # ── RAG mode: retrieve relevant chunks, then stream answer ──
            vs = load_vectorstore(current_user)
            if vs is None:
                yield "data: ⚠️ No PDF indexed yet. Upload a PDF first.\n\n"
                yield "data: [DONE]\n\n"
                return

            retriever = vs.as_retriever(search_kwargs={"k": 4})
            docs = retriever.get_relevant_documents(payload.message)
            context = "\n\n".join(d.page_content for d in docs)

            rag_prompt = (
                f"Answer the question based ONLY on the context below.\n\n"
                f"Context:\n{context}\n\n"
                f"Question: {payload.message}"
            )
            async for chunk in llm.astream(rag_prompt):
                text = chunk.content
                full_response.append(text)
                yield f"data: {text}\n\n"
        else:
            # ── Normal conversational mode with Redis history ──
            config = {"configurable": {"session_id": composite_session_key}}
            async for chunk in chain_with_history.astream(
                {"input": payload.message}, config=config
            ):
                text = chunk.content
                full_response.append(text)
                yield f"data: {text}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")