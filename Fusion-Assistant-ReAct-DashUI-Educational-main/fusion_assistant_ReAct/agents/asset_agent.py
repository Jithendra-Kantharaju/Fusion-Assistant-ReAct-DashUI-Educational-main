# fusion_assistant_ReAct/agents/asset_agent.py
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple, Callable
from pathlib import Path
import json
import re
from datetime import datetime, timezone
import pandas as pd

from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage

from email_reporting.general_report import GENERAL_REPORT_TEMPLATE
from fusion_assistant_ReAct.io.paths import DRAFT_CHECKPOINT, DRAFT_RUNS_DIR

try:
    from prompts import Asset_Disc_Prompt as DEFAULT_ASSET_TEMPLATE
except Exception:
    DEFAULT_ASSET_TEMPLATE = (
        "You write clear, professional asset emails.\n"
        "Conversation history:\n{history}\n\n"
        "Asset record (JSON):\n{asset_data}\n\n"
        "Compose a concise, helpful findings summary for the asset owner. "
        "Focus on current status, risk/impact, and actionable steps."
    )


class Asset_Discovery_Agent:
    def __init__(
        self,
        qa_chain,
        memory: Optional[ConversationBufferMemory] = None,
        excel_path: Optional[str] = None,
        recipient_match_keys: Optional[List[str]] = None,
        send_email_fn: Optional[
            Callable[[str, List[str], str, Optional[List[str]], Optional[List[str]]], None]
        ] = None,
        asset_prompt_template: Optional[str] = None,
        use_general_template: bool = True,
    ):
        self.qa_chain = qa_chain
        self.memory = memory or ConversationBufferMemory(return_messages=True)
        self.excel_path = excel_path
        self.recipient_match_keys = recipient_match_keys or ["asset_id", "hostname", "ip", "owner", "resource_owner"]
        self.send_email_fn = send_email_fn
        self.asset_prompt_template = asset_prompt_template or DEFAULT_ASSET_TEMPLATE
        self.use_general_template = use_general_template

        self._recipient_index: Optional[pd.DataFrame] = None
        self._draft_queue: List[Dict[str, Any]] = []
        self._sent_log: List[Dict[str, Any]] = []

        if self.excel_path:
            self._load_excel_index(self.excel_path)

    # ---------------- Public: single-record path ----------------
    def handle_query(self, data: Dict[str, Any]) -> Any:
        try:
            history_str = self._format_history_for_prompt(
                self.memory.load_memory_variables({}).get("history", "")
            )
            prompt = self.asset_prompt_template.format(
                history=history_str,
                asset_data=json.dumps(data, ensure_ascii=False, indent=2),
            )

            result = self.qa_chain.invoke({"input": prompt})
            findings_text = self._extract_answer_text(result).strip()

            subject = f"Asset Report: {data.get('hostname', '(unknown asset)')}"
            corrective, preventive = self._recommended_actions_sections(data)

            if self.use_general_template:
                body = self._render_general_report_email(
                    asset_data=data,
                    findings=findings_text or "No additional findings available.",
                    subject=subject,
                    corrective_actions=corrective,
                    preventive_measures=preventive,
                )
            else:
                body = findings_text

            self.memory.chat_memory.add_user_message(json.dumps(data, ensure_ascii=False))
            self.memory.chat_memory.add_ai_message(body)

            return {"answer": body, "subject": subject}
        except Exception as e:
            return {"answer": f"An error occurred while processing the asset: {e}"}

    # ---------------- Batch: dir OR single file via config ----------------
    def run_from_config(
        self,
        *,
        asset_dir: str,
        checkpoint_path: str = DRAFT_CHECKPOINT,
        subject_template: str = "Asset Review: {hostname}",
        run_id: Optional[str] = None,
        max_preview: int = 8,
    ) -> str:
        """
        Accepts either a directory (recursively scans *.jsonl) OR a single .jsonl file.
        Drafts emails, writes checkpoint, persists full drafts to drafts/runs/<run_id>.drafts.jsonl,
        and returns a concise report string (with run file path).
        """
        root = Path(asset_dir)
        if not root.exists():
            return f"[asset_discovery] Configured asset path not found: {root}"

        # Build file list
        if root.is_file() and root.suffix.lower() == ".jsonl":
            files: List[Path] = [root]
        elif root.is_dir():
            files = list(root.glob("**/*.jsonl"))
        else:
            return f"[asset_discovery] Asset path must be a directory or a .jsonl file: {root}"

        if not files:
            return f"[asset_discovery] No .jsonl files found under: {root if root.is_dir() else root.parent}"

        # Ensure output dirs exist
        Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
        Path(DRAFT_RUNS_DIR).mkdir(parents=True, exist_ok=True)

        # Preload checkpoint (dedupe)
        drafted_ids_seen = set()
        ckpt_p = Path(checkpoint_path)
        if ckpt_p.exists():
            with ckpt_p.open("r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                        if rec.get("status") == "drafted" and rec.get("id"):
                            drafted_ids_seen.add(rec["id"])
                    except Exception:
                        pass

        ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        run_id = run_id or f"run-{ts}"
        run_file = Path(DRAFT_RUNS_DIR) / f"{run_id}.drafts.jsonl"

        created = 0
        duplicates = 0
        subjects_preview: List[str] = []

        with ckpt_p.open("a", encoding="utf-8") as ckpt_fh, run_file.open("a", encoding="utf-8") as run_fh:
            for file in files:
                with file.open("r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        draft_id = self._make_draft_id(rec)
                        if draft_id in drafted_ids_seen:
                            duplicates += 1
                            continue

                        single = self.handle_query(rec)  # {"answer": body, "subject": subject}
                        body = self._extract_answer_text(single)
                        subject = self._safe_subject(subject_template, rec)

                        to_list, _meta = self._lookup_recipients(rec)
                        draft = {
                            "id": draft_id,
                            "record": rec,
                            "subject": subject,
                            "to": self._unique_emails(to_list),
                            "cc": [],
                            "bcc": [],
                            "body": body,
                            "approved": False,
                            "run_id": run_id,
                            "timestamp": ts,
                        }
                        self._draft_queue.append(draft)
                        created += 1
                        if len(subjects_preview) < max_preview:
                            subjects_preview.append(f"- {subject}")

                        # persist: checkpoint line (lightweight)
                        ckpt_fh.write(json.dumps({
                            "timestamp": ts, "run_id": run_id, "id": draft_id, "status": "drafted",
                            "hostname": rec.get("hostname"), "ip": rec.get("ip"),
                            "owner": rec.get("owner"), "resource_owner": rec.get("resource_owner"),
                            "subject": subject,
                        }, ensure_ascii=False) + "\n")

                        # persist: full draft content (heavy)
                        run_fh.write(json.dumps(draft, ensure_ascii=False) + "\n")

        root_display = str(root if root.is_dir() else root.parent)
        report_lines = [
            "Asset drafting run complete.",
            f"Run ID: {run_id}",
            f"Asset path: {root}",
            f"Scanning root: {root_display}",
            f"Checkpoint: {checkpoint_path}",
            f"Run drafts file: {run_file}",
            f"New drafts created: {created}",
            f"Skipped duplicates: {duplicates}",
        ]
        if subjects_preview:
            report_lines.append("Sample subjects:")
            report_lines.extend(subjects_preview)
        return "\n".join(report_lines)

    # ---------------- Template helpers ----------------
    def _render_general_report_email(
        self,
        *,
        asset_data: Dict[str, Any],
        findings: str,
        subject: str,
        corrective_actions: str,
        preventive_measures: str,
    ) -> str:
        return GENERAL_REPORT_TEMPLATE.format(
            recipient_name=asset_data.get("resource_owner") or asset_data.get("owner") or "Team",
            subject=subject,
            findings=findings,
            root_cause=asset_data.get("root_cause", "Investigation ongoing."),
            impact_assessment=asset_data.get("impact", "No direct impact reported."),
            corrective_actions=corrective_actions,
            preventive_measures=preventive_measures,
            sender_name="SOC Automation Agent",
            sender_title="Automated Incident Coordination System",
            sender_contact="soc-team@yourorg.com",
        )

    def _recommended_actions_sections(self, rec: Dict[str, Any]) -> Tuple[str, str]:
        status = str(rec.get("status", "")).lower()
        last_seen = str(rec.get("last_seen") or "")
        is_stale = False
        try:
            if last_seen:
                dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                is_stale = (datetime.now(timezone.utc) - dt).days >= 14
        except Exception:
            pass

        offline_or_stale_advice = (
            "- For any offline or stale agents, ensure the endpoint agent is updated and maintains an online status "
            "to reduce monitoring blind spots.\n"
        )
        corrective_items, preventive_items = [], []
        if status != "online" or is_stale:
            corrective_items.append(offline_or_stale_advice)
            preventive_items.append("- Implement a weekly stale-heartbeat check with automatic owner notification.")
        else:
            preventive_items.append("- Continue routine patching and agent health checks.")
        corrective = "\n".join(corrective_items) if corrective_items else "- No immediate corrective actions required."
        preventive = "\n".join(preventive_items) if preventive_items else "- Maintain standard monitoring cadence."
        return corrective, preventive

    # ---------------- Internals ----------------
    def _format_history_for_prompt(self, history: Any) -> str:
        try:
            if isinstance(history, list):
                parts = []
                for m in history:
                    if isinstance(m, BaseMessage):
                        role = getattr(m, "type", None) or m.__class__.__name__.replace("Message", "").lower()
                        parts.append(f"{role}: {getattr(m, 'content', '')}")
                    elif isinstance(m, dict):
                        role = m.get("type") or m.get("role") or "ai"
                        parts.append(f"{role}: {m.get('content') or m.get('text') or ''}")
                    else:
                        parts.append(str(m))
                return "\n".join(parts)
        except Exception:
            pass
        return str(history or "")

    def _extract_answer_text(self, chain_result: Any) -> str:
        if chain_result is None:
            return ""
        if isinstance(chain_result, str):
            return chain_result
        if isinstance(chain_result, dict):
            for k in ("answer", "text", "output_text", "content", "result"):
                v = chain_result.get(k)
                if isinstance(v, str):
                    return v
            return json.dumps(chain_result, ensure_ascii=False, indent=2)
        if hasattr(chain_result, "content") and isinstance(chain_result.content, str):
            return chain_result.content
        return str(chain_result)

    def _safe_subject(self, subject_template: str, rec: Dict[str, Any]) -> str:
        try:
            return subject_template.format(**rec).strip() or "Asset Review"
        except Exception:
            return "Asset Review"

    def _load_excel_index(self, path: str):
        if not path:
            self._recipient_index = None
            return
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        self._recipient_index = df

    def _lookup_recipients(self, rec: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        emails: List[str] = []
        meta: Dict[str, Any] = {}
        if self._recipient_index is None:
            return emails, meta
        for key in self.recipient_match_keys:
            value = rec.get(key)
            if value is None:
                continue
            row = self._find_excel_row(key, value)
            if row is not None:
                meta["match_key"] = key
                meta["match_value"] = value
                email_cols = [c for c in self._recipient_index.columns if str(c).lower().endswith("email")]
                for c in email_cols:
                    emails.extend(self._extract_emails_from_cell(row.get(c)))
                meta["cc"] = []
                meta["bcc"] = []
                return self._unique_emails(emails), meta
        return self._unique_emails(emails), meta

    def _find_excel_row(self, key: str, value: Any) -> Optional[Dict[str, Any]]:
        df = self._recipient_index
        if df is None:
            return None
        if key not in df.columns:
            lower_map = {c.lower(): c for c in df.columns}
            if key.lower() in lower_map:
                key = lower_map[key.lower()]
            else:
                return None
        exact = df[df[key] == value]
        if not exact.empty:
            return exact.iloc[0].to_dict()
        if isinstance(value, (list, tuple)) and value:
            any_match = df[df[key].isin(value)]
            if not any_match.empty:
                return any_match.iloc[0].to_dict()
        if isinstance(value, str):
            ci = df[df[key].astype(str).str.lower() == value.lower()]
            if not ci.empty:
                return ci.iloc[0].to_dict()
        return None

    def _extract_emails_from_cell(self, cell: Any) -> List[str]:
        if cell is None:
            return []
        text = str(cell)
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        return emails

    def _unique_emails(self, emails: Iterable[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for e in emails or []:
            e2 = str(e).strip()
            if e2 and e2.lower() not in seen:
                seen.add(e2.lower())
                out.append(e2)
        return out

    def _make_draft_id(self, rec: Dict[str, Any]) -> str:
        host = str(rec.get("hostname") or rec.get("asset_id") or rec.get("ip") or "asset")
        try:
            s = json.dumps(rec, sort_keys=True)
        except Exception:
            s = str(rec)
        return f"{host}:{abs(hash(s)) % (10**8)}"
