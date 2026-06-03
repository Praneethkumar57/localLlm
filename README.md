If we use a local models we cannot store the previous chats that we made with the Local LLM's and LLM's also forgets the before messages, so this is a FastAPI + Streamlit based self-hosted AI chat platform with JWT auth. We can upload documnets also for Rag based Q&A model. I used Llama 3.2 local model with nomic embeddings for chat-based responses from model. To store the data locally I used redis with RunnableWithMessageHistory to access user data and storing them locally.

Requirements:
streamlit
langchain-huggingface
langchain-community
faiss-cpu
pypdf
langchain-text-splitters
python-dotenv
sentence-transformers
langchain-classic
langchain-core
langchain
langchain-ollama
tqdm
networkx
matplotlib
redis
fastapi
python-jose[cryptography]
passlib
python-multipart
requests
