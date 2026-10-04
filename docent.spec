# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Docent desktop app.   Build:  pyinstaller docent.spec --noconfirm"""
import sys

from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = [], [], []

# Packages that load data files / plugins dynamically.
for pkg in ("streamlit", "chromadb", "webview", "sentence_transformers", "google.genai"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Packages that call importlib.metadata at runtime.
for dist in (
    "streamlit", "chromadb", "sentence-transformers", "transformers", "tokenizers",
    "huggingface-hub", "safetensors", "torch", "numpy", "tqdm", "regex", "requests",
    "packaging", "filelock", "pypdf", "google-genai", "pyyaml", "onnxruntime",
):
    try:
        datas += copy_metadata(dist)
    except Exception:
        pass

# app.py is executed by Streamlit as a script, so PyInstaller can't see its imports.
# Listing our own modules here makes the analysis follow their dependencies too.
hiddenimports += [
    "src.config", "src.guardrails", "src.ingestion", "src.vectorstore",
    "src.llm", "src.rag", "src.user_settings", "dotenv", "platformdirs",
]
datas += [("app.py", "."), (".streamlit", ".streamlit")]

a = Analysis(
    ["desktop/launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Docent",
    console=False,          # set True while debugging a build
    icon=None,              # e.g. "assets/docent.ico" (.icns on macOS)
)
coll = COLLECT(exe, a.binaries, a.datas, name="Docent")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Docent.app",
        icon=None,
        bundle_identifier="com.example.docent",
        info_plist={"NSHighResolutionCapable": True},
    )
