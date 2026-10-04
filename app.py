"""Streamlit UI: upload, chat with history, transparent source display."""
import hashlib
import logging
import os

import streamlit as st

from src.config import settings
from src.ingestion import SUPPORTED_EXTENSIONS, ingest_file
from src.rag import RAGPipeline
from src.ui_theme import READING_HTML, cite, empty_state, inject_theme, marker_bar
from src.user_settings import clear_api_key, load_api_key, load_theme, save_api_key, save_theme
from src.vectorstore import VectorStore

logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="Docent", page_icon="📖", layout="centered",
                   initial_sidebar_state="expanded")
st.session_state.setdefault("theme", load_theme())
inject_theme(st.session_state.theme)

# Streamlit Cloud: bridge st.secrets → env (no-op locally if no secrets file exists)
try:
    for k in ("GEMINI_API_KEY", "LLM_MODEL"):
        if k in st.secrets:
            os.environ[k] = st.secrets[k]
except Exception:
    pass


@st.cache_resource(show_spinner="Loading embedding model…")
def get_pipeline() -> RAGPipeline:
    return RAGPipeline(VectorStore())


# Desktop first-run: use the saved key, or ask for one (stored only on this computer).
if not os.getenv("GEMINI_API_KEY"):
    saved = load_api_key()
    if saved:
        os.environ["GEMINI_API_KEY"] = saved

if not os.getenv("GEMINI_API_KEY"):
    st.title("Welcome to Docent")
    st.write("Enter your Google Gemini API key to get started (free keys: https://aistudio.google.com/apikey). It is stored only on this computer.")
    entered = st.text_input("Gemini API key", type="password", placeholder="AIza...")
    if st.button("Save and continue", type="primary") and entered.strip():
        save_api_key(entered.strip())
        os.environ["GEMINI_API_KEY"] = entered.strip()
        st.rerun()
    st.stop()

pipeline = get_pipeline()

store = pipeline.store
ss = st.session_state
ss.setdefault("messages", [])        # [{"role", "content", "sources", "warnings"}]
ss.setdefault("processed", set())    # file hashes handled this session

# ───────────────────────── Sidebar ─────────────────────────
with st.sidebar:
    st.header("Library")
    files = st.file_uploader(
        "Drop PDF or Markdown files here",
        type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS],
        accept_multiple_files=True,
    )
    for f in files or []:
        data = f.getvalue()
        h = hashlib.sha256(data).hexdigest()
        if h in ss.processed:
            continue
        with st.spinner(f"Indexing {f.name}…"):
            try:
                result = ingest_file(f.name, data)
                store.add_chunks(result.chunks)
                ss.processed.add(h)
                st.success(f"{f.name}: {len(result.chunks)} passages indexed")
                if result.quarantined:
                    st.warning(
                        f"{result.quarantined} chunk(s) in {f.name} looked like "
                        "prompt-injection and were excluded."
                    )
            except Exception as e:
                st.error(f"{f.name}: {e}")

    indexed = store.list_sources()
    st.caption("Indexed files")
    if not indexed:
        st.caption("Nothing indexed yet.")
    for name, n in indexed.items():
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"**{name}**  \n{n} passages")
        if c2.button("✕", key=f"del_{name}", help="Remove from index"):
            store.delete_source(name)
            ss.processed.clear()
            st.rerun()

    selected = st.multiselect("Restrict search to", list(indexed), default=[])

    st.subheader("Search settings")
    top_k = st.slider("Passages to retrieve", 1, 10, settings.top_k)
    min_score = st.slider("Minimum match", 0.0, 0.9, settings.min_score, 0.05)

    st.radio(
        "Appearance", ["Auto", "Light", "Dark"], key="theme", horizontal=True,
        on_change=lambda: save_theme(st.session_state.theme),
        help="Auto follows your system setting.",
    )
    
    if st.button("Clear chat"):
        ss.messages = []
        st.rerun()

    with st.expander("🔑 API key"):
        if st.button("Remove saved key"):
            clear_api_key()
            os.environ.pop("GEMINI_API_KEY", None)
            get_pipeline.clear()
            st.rerun()


# ───────────────────────── Chat ─────────────────────────
def render_sources(sources: list[dict]) -> None:
    with st.expander(f"{len(sources)} source{'s' if len(sources) != 1 else ''}"):
        for i, s in enumerate(sources, start=1):
            page = f", page {s['page']}" if s["page"] else ""
            st.markdown(f"**{i}  {s['source']}**{page}")
            st.markdown(marker_bar(s["score"]), unsafe_allow_html=True)   # numbers only
            st.text(s["text"])


if not ss.messages:
    st.markdown(empty_state(bool(indexed)), unsafe_allow_html=True)       # static copy only

for m in ss.messages:
    with st.chat_message(m["role"]):
        st.markdown(cite(m["content"]) if m["role"] == "assistant" else m["content"])
        for w in m.get("warnings", []):
            st.warning(w)
        if m.get("sources"):
            render_sources(m["sources"])

if prompt := st.chat_input("Ask a question about your documents", disabled=not indexed):
    history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
    ss.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        holder = st.empty()
        holder.markdown(READING_HTML, unsafe_allow_html=True)             # marker animation
        try:
            r = pipeline.answer(
                prompt, history, sources=selected or None, top_k=top_k, min_score=min_score
            )
        except Exception as e:
            logging.exception("RAG failure")
            holder.empty()
            st.error(f"Docent couldn't answer this: {e}")
            st.stop()
        holder.empty()
        st.markdown(cite(r.answer))
        for w in r.warnings:
            st.warning(w)
        src = [
            {"source": x.source, "page": x.page, "score": x.score, "text": x.text}
            for x in r.sources
        ]
        if src:
            render_sources(src)
        if r.standalone_question and r.standalone_question != prompt:
            st.caption(f"Searched as: {r.standalone_question}")

    ss.messages.append(
        {"role": "assistant", "content": r.answer, "sources": src, "warnings": r.warnings}
    )