import streamlit as st
import requests

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="LocalMind – Private AI Chat",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

API = "http://localhost:8000/api/v1"

# ─────────────────────────────────────────────
# Custom CSS  (dark, clean, minimal)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

/* Auth card */
.auth-card {
    background: #0f0f13;
    border: 1px solid #2a2a35;
    border-radius: 16px;
    padding: 2.5rem 3rem;
    max-width: 440px;
    margin: 4rem auto;
    box-shadow: 0 0 60px rgba(99,102,241,.08);
}
.auth-title {
    font-size: 1.6rem;
    font-weight: 600;
    color: #e0e0f0;
    margin-bottom: .25rem;
    letter-spacing: -.5px;
}
.auth-sub { color: #666; font-size: .85rem; margin-bottom: 1.8rem; }

/* Sidebar polish */
[data-testid="stSidebar"] { background: #0d0d11; border-right: 1px solid #1e1e2a; }
[data-testid="stSidebar"] * { color: #c9c9d8 !important; }

/* Hide default Streamlit chrome */
#MainMenu, footer { visibility: hidden; }

/* Stream output */
.stream-box {
    font-family: 'Sora', sans-serif;
    font-size: .95rem;
    line-height: 1.7;
    color: #e0e0f0;
}

/* Pill badges */
.badge-rag {
    background: #1a1a2e;
    border: 1px solid #4f46e5;
    color: #818cf8;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: .72rem;
    font-family: 'JetBrains Mono', monospace;
    margin-left: 6px;
}
.badge-pdf {
    background: #0f2a1e;
    border: 1px solid #10b981;
    color: #34d399;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: .72rem;
    font-family: 'JetBrains Mono', monospace;
    margin-left: 6px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Helper: authenticated request headers
# ─────────────────────────────────────────────
def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.get('token', '')}"}


def api_get(path: str):
    return requests.get(f"{API}{path}", headers=auth_headers(), timeout=10)


def api_post(path: str, **kwargs):
    return requests.post(f"{API}{path}", headers=auth_headers(), timeout=30, **kwargs)


# ─────────────────────────────────────────────
# Auth Screen
# ─────────────────────────────────────────────
def render_auth():
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">🧠 LocalMind</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-sub">Private, local AI — your data never leaves your machine</div>',
                    unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        # ── Login Tab ──
        with tab_login:
            username_l = st.text_input("Username", key="login_user", placeholder="your_username")
            password_l = st.text_input("Password", key="login_pass", type="password", placeholder="••••••••")
            if st.button("Sign In →", use_container_width=True, type="primary"):
                if not username_l or not password_l:
                    st.error("Both fields are required.")
                else:
                    try:
                        r = requests.post(f"{API}/auth/login",
                                          json={"username": username_l, "password": password_l},
                                          timeout=10)
                        if r.status_code == 200:
                            data = r.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.current_user = data["username"]
                            st.rerun()
                        else:
                            try:
                                detail = r.json().get("detail", "Login failed")
                            except Exception:
                                detail = r.text or f"Login failed (HTTP {r.status_code})"
                            st.error(detail)
                    except requests.ConnectionError:
                        st.error("Cannot reach backend. Is backend.py running on port 8000?")
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")

        # ── Register Tab ──
        with tab_register:
            username_r = st.text_input("Choose a Username", key="reg_user", placeholder="min. 3 characters")
            password_r = st.text_input("Password", key="reg_pass", type="password", placeholder="min. 6 characters")
            confirm_r = st.text_input("Confirm Password", key="reg_confirm", type="password", placeholder="repeat password")
            if st.button("Create Account →", use_container_width=True, type="primary"):
                if not username_r or not password_r or not confirm_r:
                    st.error("All fields are required.")
                elif password_r != confirm_r:
                    st.error("Passwords do not match.")
                elif len(password_r) < 6:
                    st.error("Password must be at least 6 characters.")
                elif len(username_r) < 3:
                    st.error("Username must be at least 3 characters.")
                else:
                    try:
                        r = requests.post(f"{API}/auth/register",
                                          json={"username": username_r, "password": password_r},
                                          timeout=10)
                        if r.status_code == 200:
                            data = r.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.current_user = data["username"]
                            st.success("Account created! Signing you in…")
                            st.rerun()
                        else:
                            try:
                                detail = r.json().get("detail", "Registration failed")
                            except Exception:
                                detail = r.text or f"Registration failed (HTTP {r.status_code})"
                            st.error(detail)
                    except requests.ConnectionError:
                        st.error("Cannot reach backend. Is backend.py running on port 8000?")
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
def render_sidebar(sessions: dict, active_id: str, rag_ready: bool, pdf_list: list) -> str:
    with st.sidebar:
        st.markdown(f"### 🧠 LocalMind")
        st.caption(f"Signed in as **{st.session_state.current_user}**")
        st.markdown("---")

        # Logout
        if st.button("🚪 Sign Out", use_container_width=True):
            for key in ["token", "current_user", "current_session_id", "rag_mode"]:
                st.session_state.pop(key, None)
            st.rerun()

        # New chat
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            r = api_post("/sessions/new")
            if r.status_code == 200:
                st.session_state.current_session_id = r.json()["session_id"]
                st.rerun()

        st.markdown("---")

        # ── PDF Section ──
        st.markdown("#### 📄 Your Documents")
        if pdf_list:
            for pdf in pdf_list:
                st.markdown(f'<span class="badge-pdf">✓ {pdf}</span>', unsafe_allow_html=True)
        else:
            st.caption("No PDFs uploaded yet.")

        uploaded = st.file_uploader("Upload a PDF", type=["pdf"], label_visibility="collapsed")
        if uploaded:
            with st.spinner("Indexing PDF…"):
                r = requests.post(
                    f"{API}/upload-pdf",
                    headers=auth_headers(),
                    files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                    timeout=120
                )
            if r.status_code == 200:
                data = r.json()
                st.success(f"✅ Indexed {data['pages']} pages")
                st.rerun()
            else:
                st.error(r.json().get("detail", "Upload failed"))

        # RAG toggle
        st.markdown("---")
        rag_label = "🔍 Answer from PDF" if rag_ready else "🔍 PDF Mode (upload first)"
        use_rag = st.toggle(rag_label, value=st.session_state.get("rag_mode", False), disabled=not rag_ready)
        st.session_state.rag_mode = use_rag
        if use_rag:
            st.markdown('<span class="badge-rag">RAG active</span>', unsafe_allow_html=True)

        st.markdown("---")

        # ── Session List ──
        st.markdown("#### 🕒 Conversations")
        new_active = active_id
        for sess_id, title in sessions.items():
            is_active = sess_id == active_id
            label = f"{'💬' if is_active else '📁'} {title}"
            if is_active:
                st.button(label, key=f"s_{sess_id}", disabled=True, use_container_width=True)
            else:
                if st.button(label, key=f"s_{sess_id}", use_container_width=True):
                    new_active = sess_id

        return new_active


# ─────────────────────────────────────────────
# Streaming chat call
# ─────────────────────────────────────────────
def stream_response(session_id: str, message: str, use_rag: bool):
    """Yields text chunks from the SSE streaming endpoint."""
    payload = {"session_id": session_id, "message": message, "use_rag": use_rag}
    with requests.post(
        f"{API}/chat/stream",
        json=payload,
        headers=auth_headers(),
        stream=True,
        timeout=120
    ) as resp:
        if resp.status_code != 200:
            yield f"⚠️ Backend error: {resp.text}"
            return
        for line in resp.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    chunk = decoded[6:]
                    if chunk == "[DONE]":
                        return
                    yield chunk


# ─────────────────────────────────────────────
# Main Chat UI
# ─────────────────────────────────────────────
def render_chat():
    current_user = st.session_state.current_user

    # ── Fetch session list ──
    try:
        session_resp = api_get("/sessions")
        sessions = session_resp.json().get("sessions", {})
    except Exception:
        st.error("Cannot reach backend API. Ensure backend.py is running.")
        st.stop()

    # ── Ensure an active session exists ──
    if "current_session_id" not in st.session_state or \
            st.session_state.current_session_id not in sessions:
        if sessions:
            st.session_state.current_session_id = list(sessions.keys())[0]
        else:
            r = api_post("/sessions/new")
            st.session_state.current_session_id = r.json()["session_id"]
            st.rerun()

    active_id = st.session_state.current_session_id

    # ── PDF status ──
    pdf_resp = api_get("/pdfs")
    pdf_data = pdf_resp.json() if pdf_resp.status_code == 200 else {}
    pdf_list = pdf_data.get("pdfs", [])
    rag_ready = pdf_data.get("rag_ready", False)

    # ── Sidebar ──
    new_active = render_sidebar(sessions, active_id, rag_ready, pdf_list)
    if new_active != active_id:
        st.session_state.current_session_id = new_active
        st.rerun()

    # ── Header ──
    session_title = sessions.get(active_id, "Chat")
    rag_badge = ' <span class="badge-rag">RAG</span>' if st.session_state.get("rag_mode") else ""
    st.markdown(f"<h3 style='margin-bottom:.2rem;color:#e0e0f0'>{session_title}{rag_badge}</h3>",
                unsafe_allow_html=True)
    if st.session_state.get("rag_mode"):
        st.caption("📄 Responses are grounded in your uploaded PDF — toggle off for normal chat.")
    st.markdown("---")

    # ── Chat History ──
    history_resp = api_get(f"/history/{active_id}")
    chat_logs = history_resp.json().get("history", []) if history_resp.status_code == 200 else []

    for log in chat_logs:
        role = "user" if log.get("type") == "human" else "assistant"
        content = log.get("data", {}).get("content", "")
        with st.chat_message(role):
            st.markdown(content)

    # ── Live Input ──
    if user_input := st.chat_input(
        "Ask anything…" if not st.session_state.get("rag_mode") else "Ask about your PDF…"
    ):
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            collected = []

            # Stream chunks into the placeholder
            for chunk in stream_response(
                session_id=active_id,
                message=user_input,
                use_rag=st.session_state.get("rag_mode", False)
            ):
                collected.append(chunk)
                placeholder.markdown(
                    '<div class="stream-box">' + "".join(collected) + " ▌</div>",
                    unsafe_allow_html=True
                )

            # Final render without cursor
            placeholder.markdown("".join(collected))

        st.rerun()


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if "token" not in st.session_state or "current_user" not in st.session_state:
    render_auth()
else:
    render_chat()
