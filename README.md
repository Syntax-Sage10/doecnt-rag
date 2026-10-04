# 📄 Document Q&A Chatbot

Grounded RAG over your PDFs and Markdown files, with numbered citations and an explicit
"I don't know based on the provided documents." when the answer isn't in the sources.

## Features
- Drag-and-drop PDF / Markdown / text upload
- Strict grounding: answers only from retrieved context
- Numbered citations + expandable source chunks with similarity scores
- Prompt-injection screening of uploaded documents
- LLM-as-a-judge evaluation (context relevance, faithfulness)

## Architecture

```
Upload ─► Parse ─► Guardrail scan ─► Chunk ─► Embed ─► ChromaDB
Question ─► Condense ─► Embed ─► Top-k ─► Score gate ─► Strict prompt ─► LLM ─► Citation check ─► UI
```

| Component | Technology |
|---|---|
| UI | Streamlit |
| Vector DB | ChromaDB (persistent, cosine) |
| Embeddings | BAAI/bge-small-en-v1.5 (local) |
| LLM | Google Gemini |

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # add GEMINI_API_KEY
streamlit run app.py
```

## Configuration
All tunables live in `src/config.py` (chunk size/overlap, top-k, `min_score`, models).
Override models and paths with environment variables (see `.env.example`).

## How it works
1. **Ingestion**: parse, scan for injection phrasing, chunk (1000 chars / 150 overlap).
2. **Retrieval gate**: if no chunk clears `min_score`, refuse without calling the LLM.
3. **Grounded generation**: strict system prompt, context wrapped as untrusted data.
4. **Citation validation**: warn on citations that don't map to retrieved chunks.

## Security model
Threats: indirect prompt injection, data exfiltration, cross-user leakage.
Mitigations: delimiter sanitization, ingestion-time screening, no tool access,
exfiltration rules in the prompt, upload limits. Add auth and per-user filtering
before any multi-user deployment.

## Evaluation
```bash
python -m src.evaluation eval/golden_set.jsonl
```
Low relevance → tune retrieval. Low faithfulness → tune prompt/model.
Include unanswerable questions and confirm they are refused.

## Testing
```bash
pytest -q
```

## Deployment
**Streamlit Community Cloud**: push to GitHub, create app with `app.py`, add
`GEMINI_API_KEY` under Secrets.

**Hugging Face Spaces (Docker)**: create a Docker Space, push this repo, and add this
YAML block at the very top of the Space's README:
```yaml
---
title: Document QA
sdk: docker
app_port: 7860
---
```
Add `GEMINI_API_KEY` as a Secret. Disk is ephemeral on free tiers, so the index
resets on restart.

## Roadmap
Cross-encoder reranker · hybrid BM25 · OCR for scanned PDFs · auth + per-user
collections · streaming responses

## 🖥️ Desktop app (Windows / macOS / Linux)

Docent also ships as a native desktop app: a Streamlit server runs locally
(127.0.0.1 only) inside a native window (`pywebview`). Your documents and the vector
index stay on your machine; only the question and retrieved passages go to the LLM API.

**Run the desktop version from source**
```bash
pip install -r requirements.txt -r requirements-desktop.txt
python desktop/launcher.py
```

**Build an installer locally**
```bash
pyinstaller docent.spec --noconfirm        # → dist/Docent/ (and dist/Docent.app on macOS)
```
Windows installer: install [Inno Setup](https://jrsoftware.org/isinfo.php), then
`ISCC /DAppVersion=0.1.0 installer\docent.iss`.

**Build for all three OSes with CI**: push a tag; GitHub Actions builds and publishes
a Windows installer, macOS `.dmg`, and Linux `.tar.gz` to the Release.
```bash
git tag v0.1.0 && git push origin v0.1.0
```

**Where data lives:** index and models in the OS user-data/cache folders, API key in
the OS user-config folder (`settings.json`), logs in the OS log folder (`docent.log`).

**Notes**
- First launch downloads the ~130 MB embedding model (needs internet once).
- Builds are unsigned. Windows SmartScreen and macOS Gatekeeper will warn until you
  code-sign (Apple Developer ID / Windows certificate).
- Windows needs the Edge WebView2 runtime (preinstalled on current Windows 10/11).
# doecnt-rag
