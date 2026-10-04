"""Docent look & feel: one stylesheet plus small HTML helpers.

SECURITY: everything injected with unsafe_allow_html must be a static constant or built
from numbers only. Never interpolate document text, filenames, or model output into it.
"""
import re

import streamlit as st

_FONTS = (
    "@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;"
    "0,6..72,600;1,6..72,400&family=Instrument+Sans:wght@400;500;600&display=swap');"
)

CSS = _FONTS + """
:root{--ink:#16213E;--paper:#F5F7FA;--panel:#EAEEF5;--surface:#FFFFFF;--line:#D5DBE6;--accent:#3A47D5;--mark:#FFE066;--mute:#5B6578}
.stApp,.stApp p,.stApp label,.stApp li,.stApp button,.stApp input,.stApp textarea{font-family:'Instrument Sans',system-ui,sans-serif}
.block-container{max-width:50rem;padding-top:2.5rem}
#MainMenu,footer,[data-testid="stAppDeployButton"]{display:none}
[data-testid="stHeader"]{background:transparent}
h1,h2,h3{font-family:'Newsreader',Georgia,serif!important;letter-spacing:-.01em;color:var(--ink)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
[data-testid="stSidebar"]{border-right:1px solid var(--line)}
[data-testid="stSidebar"] h2{font-size:1.5rem}

/* conversation: answers are set like book text; questions sit in the margin */
[data-testid="stChatMessageAvatarUser"],[data-testid="stChatMessageAvatarAssistant"]{display:none}
[data-testid="stChatMessage"]{background:transparent;padding:.3rem 0 1.2rem;gap:0}
[data-testid="stChatMessage"] p,[data-testid="stChatMessage"] li{font-family:'Newsreader',Georgia,serif;font-size:1.12rem;line-height:1.7;max-width:66ch}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){border-left:3px solid var(--mark);padding-left:1rem}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p{font-family:'Instrument Sans',system-ui,sans-serif;font-size:1rem;color:var(--mute)}
[data-testid="stChatInput"]{transition:box-shadow .2s}
[data-testid="stChatInput"]:focus-within{box-shadow:0 0 0 2px var(--accent)}

/* controls */
.stButton>button{border-radius:8px;transition:transform .15s,box-shadow .15s}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 4px 12px -6px rgba(22,33,62,.4)}
.stButton>button:active{transform:none}
[data-testid="stFileUploaderDropzone"]{border:1.5px dashed var(--accent);background:rgba(58,71,213,.04);transition:background .25s}
[data-testid="stFileUploaderDropzone"]:hover{background:rgba(255,224,102,.3)}
[data-testid="stExpander"]{border:1px solid var(--line);border-radius:10px;background:var(--surface)}

/* the marker: empty state, loading state, source match bars */
.dc-empty{padding:3rem 0 .5rem}
.dc-empty h1{font-size:2.6rem;margin:0 0 .5rem}
.dc-empty p{color:var(--mute);max-width:46ch;line-height:1.6;font-size:1.05rem}
.dc-page{width:min(300px,100%);padding:.9rem 1.2rem;margin-bottom:1.8rem;background:var(--surface);border:1px solid var(--line);border-radius:6px;box-shadow:0 14px 30px -20px rgba(22,33,62,.45)}
.dc-page .l,.dc-reading .l{position:relative;display:block;height:7px;margin:1rem 0;border-radius:3px;background:var(--line)}
.dc-page .l::after,.dc-reading .l::after{content:"";position:absolute;inset:-4px -3px;border-radius:2px;background:var(--mark);mix-blend-mode:multiply;transform-origin:left;transform:scaleX(0);
  animation:dc-sweep var(--t,9s) ease-in-out infinite;animation-delay:calc(var(--n)*var(--s,1.1s))}
.dc-reading{--t:2.2s;--s:.25s;max-width:30rem;padding:.3rem 0 1rem}
.dc-reading .l{background:var(--panel);margin:.8rem 0}
.dc-reading p{margin:.2rem 0 0;color:var(--mute);font-size:.95rem}
@keyframes dc-sweep{0%{transform:scaleX(0);opacity:.9}12%,55%{transform:scaleX(1);opacity:.9}70%,100%{transform:scaleX(1);opacity:0}}
.dc-bar{display:flex;align-items:center;gap:.6rem;margin:.1rem 0 .5rem;color:var(--mute);font-size:.85rem}
.dc-bar .t{flex:0 0 120px;height:9px;border-radius:2px;background:var(--panel)}
.dc-bar i{display:block;height:100%;border-radius:2px;background:var(--mark)}
@media (prefers-reduced-motion:reduce){
  .dc-page .l::after,.dc-reading .l::after{animation:none;transform:scaleX(1);opacity:.6}
  .stButton>button{transition:none}
}
"""

# Dark = overrides on top of CSS. Streamlit paints most widgets itself, so each surface is listed.
_DARK = """
:root{color-scheme:dark;--ink:#E6EAF5;--paper:#0F1424;--panel:#1B2238;--surface:#161C30;--line:#2C3552;--accent:#8B95FF;--mute:#9AA5C0}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stBottom"],[data-testid="stBottom"]>div,[data-testid="stBottomBlockContainer"]{background:var(--paper)!important}
[data-testid="stSidebar"],[data-testid="stSidebar"]>div{background:var(--surface)!important}
.stApp,.stApp p,.stApp li,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp small,[data-testid="stText"],[data-testid="stAlert"] *,[data-testid="stHeader"] button{color:var(--ink)!important}
[data-testid="stCaptionContainer"],.dc-empty p,.dc-bar,.dc-reading p,[data-testid="stFileUploaderDropzone"] small,[data-testid="stFileUploaderDropzoneInstructions"] *,[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p{color:var(--mute)!important}
[data-testid="stBaseButton-secondary"],[data-testid="stBaseButton-secondaryFormSubmit"]{background:var(--panel)!important;border:1px solid var(--line)!important}
[data-testid="stBaseButton-secondary"] *,[data-testid="stBaseButton-secondaryFormSubmit"] *{color:var(--ink)!important}
[data-testid="stBaseButton-primary"]{background:var(--accent)!important;border-color:var(--accent)!important}
[data-testid="stBaseButton-primary"] *{color:#0F1424!important}
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],[data-testid="stChatInput"]>div{background:var(--panel)!important}
input,textarea{color:var(--ink)!important;-webkit-text-fill-color:var(--ink)!important}
input::placeholder,textarea::placeholder{color:var(--mute)!important;-webkit-text-fill-color:var(--mute)!important;opacity:1}
[data-testid="stChatInputSubmitButton"]{background:transparent!important;border:0!important}
[data-testid="stChatInputSubmitButton"] *{color:var(--ink)!important}
[data-baseweb="select"] *{background-color:var(--panel)!important;color:var(--ink)!important}
[data-baseweb="tag"],[data-baseweb="tag"] *{background-color:var(--accent)!important;color:#0F1424!important}
[data-baseweb="popover"] *,[data-baseweb="menu"] *{background-color:var(--surface)!important;color:var(--ink)!important}
[data-testid="stExpander"],[data-testid="stExpander"] summary,[data-testid="stExpander"] details{background:var(--surface)!important;border-color:var(--line)!important}
[data-testid="stExpander"] *{color:var(--ink)!important}
[data-testid="stExpander"] .dc-bar{color:var(--mute)!important}
[data-testid="stFileUploaderDropzone"]{background:rgba(139,149,255,.08)!important}
[data-testid="stFileUploaderDropzone"]:hover{background:rgba(255,224,102,.12)!important}
.dc-page{background:var(--surface)!important}
.dc-page .l{background:#3A4468}
.dc-reading .l{background:#2C3552}
.dc-page .l::after,.dc-reading .l::after{mix-blend-mode:normal;background:rgba(255,224,102,.6)}
"""

THEMES = ("Auto", "Light", "Dark")

READING_HTML = (
    '<div class="dc-reading" role="status">'
    '<span class="l" style="--n:0;width:92%"></span><span class="l" style="--n:1;width:78%"></span>'
    '<span class="l" style="--n:2;width:85%"></span><p>Reading your documents</p></div>'
)

_SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def theme_css(mode: str = "Auto") -> str:
    """Light is the base. Dark = overrides; Auto = overrides only if the OS prefers dark.
    Only fixed constants are ever returned, whatever `mode` is."""
    if mode == "Dark":
        return CSS + _DARK
    if mode == "Auto":
        return CSS + "@media (prefers-color-scheme: dark){" + _DARK + "}"
    return CSS


def inject_theme(mode: str = "Auto") -> None:
    st.markdown(f"<style>{theme_css(mode)}</style>", unsafe_allow_html=True)


def empty_state(has_documents: bool) -> str:
    title = "Ask your documents" if has_documents else "Add a document to begin"
    body = (
        "Type a question below. Every answer cites the passages it came from, "
        "and Docent says so when the answer isn't there."
        if has_documents
        else "Drop PDF or Markdown files into the sidebar. They are indexed on this machine, "
        "and answers come only from what you add."
    )
    lines = "".join(
        f'<span class="l" style="--n:{n};width:{w}%"></span>'
        for n, w in enumerate((90, 100, 68, 96, 55))
    )
    return (
        f'<div class="dc-empty"><div class="dc-page" aria-hidden="true">{lines}</div>'
        f"<h1>{title}</h1><p>{body}</p></div>"
    )


def marker_bar(score: float) -> str:
    pct = int(max(0.0, min(float(score), 1.0)) * 100)      # numeric only: safe to inject
    return (
        f'<div class="dc-bar"><span class="t"><i style="width:{pct}%"></i></span>'
        f"{score:.2f} match</div>"
    )


def cite(text: str) -> str:
    """Display-only: turn [1] into a footnote-style ⁽¹⁾ (stored text keeps [1])."""
    return re.sub(r"\[(\d+)\]", lambda m: "⁽" + m.group(1).translate(_SUP) + "⁾", text)