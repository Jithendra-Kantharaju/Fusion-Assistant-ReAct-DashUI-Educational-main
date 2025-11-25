# dash-ui-ReAct.py — terminal-style chat using a ReAct agent (single entry point)
import os
from datetime import datetime
from pathlib import Path
import json
import uuid
from typing import Optional, Dict, Any

import dash
from dash import Dash, html, dcc, Input, Output, State, no_update
import dash_bootstrap_components as dbc

from langchain.schema import Document
from fusion_assistant_ReAct.app import simulate_group_chat_and_store, react_executor
from fusion_assistant_ReAct.groups import GroupChatSystem
from fusion_assistant_ReAct.io.paths import STORAGE_PATH, RETRIEVAL_LOG, DRAFT_RUNS_DIR

# -----------------------
# Per-session state store
# -----------------------
# Each browser session gets its own dict with:
#   {
#     "documents": Dict[str, Document],
#     "group_chats": Dict[str, GroupChatSystem],
#   }
#
# NOTE: This is per-process (per worker). For true cross-worker sharing,
# back with Redis/DB. For now, this isolates users within a worker.
SESSION_STATE: Dict[str, Dict[str, Any]] = {}

def _get_state(session_id: str) -> Dict[str, Any]:
    """Get or initialize per-session state."""
    state = SESSION_STATE.setdefault(session_id, {})
    docs = state.setdefault("documents", {})
    groups = state.setdefault("group_chats", {})

    # Bootstrap default "Scratchpad"
    if "Scratchpad" not in docs:
        docs["Scratchpad"] = Document(page_content="", metadata={"filename": "Scratchpad"})
    if "Scratchpad" not in groups:
        groups["Scratchpad"] = GroupChatSystem(react_executor)

    return state

def _now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

TERM_COLORS = {"bg":"#0b0f14","fg":"#e6edf3","dim":"#9aa4b2","sep":"#1a2230","u":"#8db3ff","a":"#8df6bd"}
S_TERM_CONTAINER = {"height":"50vh","overflowY":"auto","background":TERM_COLORS["bg"],"color":TERM_COLORS["fg"],
                    "border":f"1px solid {TERM_COLORS['sep']}","borderRadius":"8px","padding":"10px",
                    "fontFamily":"ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace",
                    "lineHeight":"1.35"}
S_TERM_MSG = {"padding":"8px 0","borderBottom":f"1px solid {TERM_COLORS['sep']}"}
S_TERM_HEAD = {"fontSize":"12px","color":TERM_COLORS["dim"],"marginBottom":"6px","display":"flex","gap":"6px","alignItems":"baseline"}
S_TERM_PRE = {"margin":"0","whiteSpace":"pre-wrap","wordBreak":"break-word","fontSize":"13px"}

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.config.prevent_initial_callbacks = "initial_duplicate"

# -------- Retrieval helpers --------
def _read_recent_retrievals(limit: int = 30):
    items = []
    p = Path(RETRIEVAL_LOG)
    if not p.exists():
        return items
    try:
        with p.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()[-limit:]
        for line in lines:
            try:
                rec = json.loads(line)
                items.append(rec)
            except Exception:
                continue
    except Exception:
        pass
    return items

def _pretty_query(qval: str) -> str:
    """Pretty-print JSON-encoded queries but gracefully show raw strings."""
    try:
        obj = json.loads(qval) if isinstance(qval, str) else qval
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(qval)

def _doc_title(md: dict) -> str:
    """Build a compact, readable title out of metadata."""
    path = md.get("path") or md.get("filename") or md.get("id") or "(unknown)"
    dataset = md.get("dataset") or md.get("source") or md.get("source_name") or ""
    retr = md.get("_retriever") or md.get("origin") or ""
    bits = [path]
    if dataset: bits.append(f"[{dataset}]")
    if retr: bits.append(f"‹{retr}›")
    return " ".join(bits)

def _render_retrieval_log(items):
    if not items:
        return html.Div("No retrieval log entries yet.")
    rows = []
    # newest first
    for i, rec in enumerate(reversed(items), 1):
        ts = rec.get("ts") or rec.get("timestamp") or rec.get("time") or ""
        query_raw = rec.get("query") or rec.get("q") or ""
        result_count = rec.get("result_count")
        by_source = rec.get("by_source") or {}

        # Header badges
        header_badges = []
        if result_count is not None:
            header_badges.append(dbc.Badge(f"{result_count} docs", color="primary", className="me-1"))
        if isinstance(by_source, dict):
            for src, cnt in by_source.items():
                header_badges.append(dbc.Badge(f"{src}: {cnt}", color="secondary", className="me-1"))

        header = html.Div(
            [
                html.Span(f"{i}. Retrieval at {ts}", style={"fontWeight":600}),
                html.Div(header_badges, style={"display":"inline-block", "marginLeft":"8px"})
            ],
            style={"display":"flex","alignItems":"center","flexWrap":"wrap","gap":"6px"}
        )

        # Query section
        query_section = html.Div(
            [html.Strong("Query:"), html.Pre(_pretty_query(query_raw), style=S_TERM_PRE)],
            className="mb-2"
        )

        # Documents section
        doc_items = []
        for j, d in enumerate(rec.get("docs", []), 1):
            preview = (d.get("content_preview") or "")
            if isinstance(preview, str):
                # guard length; keep generous but not unbounded
                preview = preview[:2000]
            md = d.get("metadata") or {}
            doc_header = _doc_title(md) or f"Doc {j}"

            # metadata lines (skip huge values)
            meta_lines = []
            for k, v in md.items():
                vs = str(v)
                if len(vs) > 300:
                    vs = vs[:300] + "…"
                meta_lines.append(html.Div([html.Strong(f"{k}: "), html.Code(vs)]))

            doc_items.append(
                dbc.AccordionItem(
                    [
                        html.Div(meta_lines, className="mb-2"),
                        html.Div([html.Strong("Preview:")], className="mb-1"),
                        html.Pre(preview or "(empty)", style=S_TERM_PRE),
                    ],
                    title=f"{j}. {doc_header}",
                )
            )

        docs_section = html.Div(
            [
                html.Div(html.Strong("Retrieved documents"), className="mb-1"),
                dbc.Accordion(doc_items or [dbc.AccordionItem("(none)", title="No documents")],
                              start_collapsed=True, always_open=False),
            ],
            className="mb-2"
        )

        rows.append(
            dbc.AccordionItem(
                [query_section, docs_section],
                title=header
            )
        )
    return dbc.Accordion(rows, start_collapsed=True, always_open=False)

# -------- Drafts viewer helpers --------
def _list_run_files():
    root = Path(DRAFT_RUNS_DIR)
    if not root.exists():
        return []
    return sorted([p for p in root.glob("*.drafts.jsonl")], key=lambda p: p.name)

def _load_run_drafts(run_file_path: str, limit: Optional[int] = None):
    items = []
    p = Path(run_file_path)
    if not p.exists():
        return items
    with p.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            try:
                items.append(json.loads(line))
            except Exception:
                continue
            if limit and len(items) >= limit:
                break
    return items

def _render_drafts(items):
    if not items:
        return html.Div("No drafts in this run.")
    acc_items = []
    for idx, d in enumerate(items, 1):
        subj = d.get("subject", "(no subject)")
        host = (d.get("record") or {}).get("hostname", "")
        header = f"{idx}. {subj} — {host}"
        body_pre = html.Pre(d.get("body", ""), style=S_TERM_PRE)
        meta = html.Div([
            html.Div([html.Strong("To: "), html.Code(", ".join(d.get("to", [])) or "(none)")]),
            html.Div([html.Strong("CC: "), html.Code(", ".join(d.get("cc", [])) or "(none)")]),
            html.Div([html.Strong("BCC: "), html.Code(", ".join(d.get("bcc", [])) or "(none)")]),
            html.Div([html.Strong("Run ID: "), html.Code(d.get("run_id", ""))]),
            html.Div([html.Strong("Draft ID: "), html.Code(d.get("id", ""))]),
            html.Div([html.Strong("Timestamp: "), html.Code(d.get("timestamp", ""))]),
        ], className="mb-2")
        acc_items.append(dbc.AccordionItem([meta, body_pre], title=header))
    return dbc.Accordion(acc_items, start_collapsed=True, always_open=False)

def sidebar():
    # file-select options are session-specific; we’ll populate via callbacks
    return dbc.Card(
        dbc.CardBody([
            html.H5("📂 Data", className="card-title"),
            dcc.RadioItems(
                id="load-mode",
                options=[
                    {"label": "None", "value": "none"},
                    {"label": "Upload file(s)", "value": "upload"},
                    {"label": "Enter directory path", "value": "dir"},
                ],
                value="none", inline=True,
            ),
            html.Div(id="load-area"),
            html.Hr(),
            html.Label("Active document"),
            dcc.Dropdown(id="file-select", options=[], value=None, clearable=False),
            html.Hr(),
            html.Details([
                html.Summary("✍️ Edit document text"),
                dcc.Textarea(id="doc-text", value="", style={"width":"100%","height":200}),
                html.Br(),
                dbc.Button("Save document text", id="save-doc", color="secondary", size="sm", className="mt-2"),
                html.Div(id="save-msg", className="text-success mt-2"),
            ], open=True),
            html.Hr(),
            html.H5("🔎 Retrieval trace"),
            html.Div(id="retrieval-log-panel"),
            dbc.Button("Refresh retrieval log", id="refresh-retrieval", size="sm", className="mt-2"),
            html.Div(id="retrieval-msg", className="text-muted mt-2"),

            # --- Optional: uncomment to auto-refresh every 10s ---
            # dcc.Interval(id="retrieval-interval", interval=10_000, n_intervals=0),
            # -----------------------------------------------------

            html.Hr(),
            html.H5("📧 Drafts Viewer"),
            dcc.Dropdown(id="run-select", options=[], placeholder="Select a run…"),
            dbc.Button("Refresh runs", id="refresh-runs", size="sm", className="mt-2"),
            html.Div(id="runs-msg", className="text-muted mt-2"),
            html.Div(id="drafts-panel", className="mt-2"),
        ]),
        className="h-100",
    )

def chat_panel():
    return dbc.Card(
        dbc.CardBody([
            html.H4("💬 Fusion Team Assistant"),
            html.Div(id="doc-caption", className="text-muted mb-2"),
            html.Div(id="chat-history", style=S_TERM_CONTAINER),
            dcc.Textarea(
                id="input-field",
                placeholder="Ask anything. The agent will decide whether to draft asset emails from backend config…",
                style={"width":"100%","height":100},
            ),
            dbc.ButtonGroup([
                dbc.Button("Send", id="send-btn", color="primary"),
                dbc.Button("Clear", id="clear-btn", color="secondary"),
            ]),
            html.Span(id="send-status", className="ms-3 text-muted"),
            html.Div(id="error-msg", className="text-danger mt-2"),

            # Per-session stores
            dcc.Store(id="session-id"),
            dcc.Store(id="doc-filename"),   # active filename for this session
            dcc.Store(id="doc-content"),
            dcc.Store(id="st-refresh-chat"),
        ])
    )

app.layout = dbc.Container(
    fluid=True,
    children=[dbc.Row([dbc.Col(sidebar(), width=3), dbc.Col(chat_panel(), width=9)], className="g-3 mt-3")],
)

# --------------------------
# Session bootstrap callback
# --------------------------
@app.callback(
    Output("session-id", "data"),
    Input("chat-history", "children"),
    State("session-id", "data"),
    prevent_initial_call=False,
)
def ensure_session_id(_rendered, sid):
    """Guarantee a session-id per browser tab."""
    if sid:
        return sid
    return str(uuid.uuid4())

# ---------- Retrieval log: initial + refresh ----------
@app.callback(
    Output("retrieval-log-panel", "children"),
    Output("retrieval-msg", "children"),
    Input("refresh-retrieval", "n_clicks"),
    prevent_initial_call=False,
)
def refresh_retrieval(_n):
    items = _read_recent_retrievals(limit=40)
    panel = _render_retrieval_log(items)
    path_note = f"Reading from: {RETRIEVAL_LOG} — {len(items)} recent entr{'y' if len(items)==1 else 'ies'}"
    return panel, path_note

# ---------- Runs list + load drafts ----------
@app.callback(
    Output("run-select", "options"),
    Output("runs-msg", "children"),
    Input("refresh-runs", "n_clicks"),
    prevent_initial_call=False,
)
def refresh_runs(_n):
    files = _list_run_files()
    opts = [{"label": f.name.replace(".drafts.jsonl",""), "value": str(f)} for f in files]
    root_note = f"Run files directory: {DRAFT_RUNS_DIR}"
    return opts, root_note

@app.callback(
    Output("drafts-panel", "children"),
    Input("run-select", "value"),
    prevent_initial_call=True,
)
def load_selected_run(run_file_path):
    if not run_file_path:
        return html.Div("Select a run to view drafts.")
    items = _load_run_drafts(run_file_path)
    return _render_drafts(items)

# ---------- Dynamic load area ----------
@app.callback(Output("load-area","children"), Input("load-mode","value"))
def render_load_area(mode):
    if mode == "upload":
        return html.Div([
            dcc.Upload(
                id="upload-files",
                children=html.Div(["Drag and drop or ", html.A("select files (.txt, .csv, .jsonl)")]),
                multiple=True,
                style={"width":"100%","height":"70px","lineHeight":"70px","borderWidth":"1px","borderStyle":"dashed",
                       "borderRadius":"5px","textAlign":"center"},
            ),
            html.Div(id="upload-msg", className="text-success mt-2"),
        ])
    if mode == "dir":
        return html.Div([
            dbc.Input(id="dir-path", placeholder="Server directory", type="text"),
            dbc.Button("Load directory", id="load-dir-btn", size="sm", className="mt-2"),
            html.Div(id="dir-msg", className="text-success mt-2"),
        ])
    return html.Div("")

# Upload handler (per-session)
@app.callback(
    Output("upload-msg","children"),
    Output("file-select","options", allow_duplicate=True),
    Output("file-select","value", allow_duplicate=True),
    Input("upload-files","contents"),
    State("upload-files","filename"),
    State("session-id","data"),
    prevent_initial_call=True,
)
def handle_upload(contents, filenames, session_id):
    if not contents or not session_id:
        return no_update, no_update, no_update
    state = _get_state(session_id)
    docs = state["documents"]

    added = 0
    last = None
    for content, fn in zip(contents, filenames):
        import base64
        header, b64 = content.split(",", 1)
        data = base64.b64decode(b64)
        try:
            text = data.decode("utf-8")
        except Exception:
            try:
                text = data.decode("latin-1")
            except Exception:
                continue
        docs[fn] = Document(page_content=text, metadata={"filename": fn})
        state["group_chats"].setdefault(fn, GroupChatSystem(react_executor))
        added += 1
        last = fn

    opts = [{"label": name, "value": name} for name in docs.keys()]
    if last is None:
        return "No readable files.", opts, no_update
    return f"Loaded {added} file(s).", opts, last

# Directory loader (per-session)
@app.callback(
    Output("dir-msg","children"),
    Output("file-select","options", allow_duplicate=True),
    Output("file-select","value", allow_duplicate=True),
    Input("load-dir-btn","n_clicks"),
    State("dir-path","value"),
    State("session-id","data"),
    prevent_initial_call=True,
)
def handle_dir(n, dir_path, session_id):
    if not n:
        return no_update, no_update, no_update
    if not dir_path or not os.path.isdir(dir_path):
        return "Invalid directory.", no_update, no_update

    state = _get_state(session_id)
    docs = state["documents"]
    groups = state["group_chats"]

    added = 0
    last = None
    for root, _, files in os.walk(dir_path):
        for fname in files:
            if not fname.lower().endswith((".txt", ".csv", ".jsonl")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except Exception:
                continue
            docs[fname] = Document(page_content=content, metadata={"filename": fname})
            groups.setdefault(fname, GroupChatSystem(react_executor))
            added += 1
            last = fname

    opts = [{"label": name, "value": name} for name in docs.keys()]
    if added:
        return f"Loaded {added} file(s).", opts, last
    return "No matching files found.", opts, no_update

# Populate file dropdown on session start (and whenever session-id changes)
@app.callback(
    Output("file-select", "options"),
    Output("file-select", "value"),
    Input("session-id", "data"),
    prevent_initial_call=False,
)
def init_file_dropdown(session_id):
    if not session_id:
        return [], None
    state = _get_state(session_id)
    docs = state["documents"]
    opts = [{"label": name, "value": name} for name in docs.keys()]
    # default active file
    return opts, "Scratchpad"

# Selecting active doc
@app.callback(
    Output("doc-text","value"),
    Output("doc-caption","children"),
    Output("doc-filename","data"),
    Output("doc-content","data"),
    Input("file-select","value"),
    State("session-id","data"),
    prevent_initial_call=False,
)
def on_select_file(filename, session_id):
    if not session_id:
        return "", "No session.", None, ""
    state = _get_state(session_id)
    docs = state["documents"]

    if not filename or filename not in docs:
        filename = "Scratchpad"

    doc = docs[filename]
    caption = f"Document: `{filename}`"
    return doc.page_content, caption, filename, doc.page_content

# Save edited doc
@app.callback(
    Output("save-msg","children"),
    Output("doc-content","data", allow_duplicate=True),
    Input("save-doc","n_clicks"),
    State("file-select","value"),
    State("doc-text","value"),
    State("session-id","data"),
    prevent_initial_call=True,
)
def save_doc(n, filename, new_text, session_id):
    if not n or not session_id:
        return no_update, no_update
    state = _get_state(session_id)
    docs = state["documents"]
    if filename not in docs:
        return "Unknown document.", no_update
    docs[filename].page_content = new_text or ""
    return "Document updated.", docs[filename].page_content

def _render_history(group: GroupChatSystem):
    history = list(getattr(group, "chat_history", []))
    total = len(history)
    nodes = []
    for idx, msg in enumerate(history):
        who = str(msg.get("user","assistant")).lower()
        role_name = "User" if who in ("user","human") else "Assistant"
        role_color = TERM_COLORS["u"] if role_name == "User" else TERM_COLORS["a"]
        raw = msg.get("message","")
        content_text = raw if isinstance(raw, str) else str(raw)
        head_style = dict(S_TERM_HEAD)
        role_style = {"color": role_color, "fontWeight": 600}
        msg_style = dict(S_TERM_MSG)
        if idx == total - 1:
            msg_style["borderBottom"] = "none"
        nodes.append(html.Div([
            html.Div([html.Span(role_name, style=role_style), html.Span("•", style={"opacity":0.6}),
                      html.Span(_now_iso(), style={"opacity":0.6})], style=head_style),
            html.Pre(content_text, style=S_TERM_PRE),
        ], style=msg_style))
    return nodes

@app.callback(
    Output("chat-history","children"),
    Input("doc-filename","data"),
    State("session-id","data"),
    prevent_initial_call=False,
)
def refresh_chat(filename, session_id):
    if not session_id:
        return []
    state = _get_state(session_id)
    groups = state["group_chats"]
    group = groups.setdefault(filename or "Scratchpad", GroupChatSystem(react_executor))
    return _render_history(group)

@app.callback(Output("input-field","value"), Input("clear-btn","n_clicks"), prevent_initial_call=True)
def clear_input(n): return ""

# SEND: single entry point to ReAct executor (per-session)
@app.callback(
    Output("send-status","children"),
    Output("st-refresh-chat","data"),
    Output("chat-history","children", allow_duplicate=True),
    Output("input-field","value", allow_duplicate=True),
    Input("send-btn","n_clicks"),
    State("input-field","value"),
    State("doc-filename","data"),
    State("doc-content","data"),
    State("session-id","data"),
    prevent_initial_call=True,
)
def on_send(n, user_text, filename, doc_content, session_id):
    if not n:
        return no_update, no_update, no_update, no_update
    text = (user_text or "").strip()
    if not text:
        return "Please enter a message.", no_update, no_update, no_update
    if not session_id:
        return "Missing session.", no_update, no_update, no_update

    state = _get_state(session_id)
    groups = state["group_chats"]
    group = groups.setdefault(filename or "Scratchpad", GroupChatSystem(react_executor))
    try:
        simulate_group_chat_and_store(group, STORAGE_PATH, text, filename or "Scratchpad", doc_content or "")
        return ("✅ Sent.", _now_iso(), _render_history(group), "")
    except Exception as e:
        return f"Error: {e}", no_update, no_update, no_update
    
# server = app.server

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8050"))
    # Bind to all interfaces so you can reach it from other machines on the network/VPN
    app.run(debug=True, host="0.0.0.0", port=port)
