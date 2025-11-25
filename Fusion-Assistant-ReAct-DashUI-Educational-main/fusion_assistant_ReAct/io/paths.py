"""
Central place for data/index locations with easy env overrides.

You can override any path via environment variables, e.g.:
  export SCENARIO1_DIR=/data/scenario1
  export SIGMA_DIR="/data/Sigma Exploiot rules/Sigma_Exploiot_rules"
  export CVE_DIR=/data/cve
  export CHAT_HISTORY_PATH=/var/app/char_history.json
"""

import os

# === storage ===
STORAGE_PATH = os.getenv("CHAT_HISTORY_PATH", "char_history.json")

# === source data dirs (match your original monolith defaults) ===
SCENARIO1_DIR = os.getenv("SCENARIO1_DIR", "Scenario1_data")
SIGMA_DIR     = os.getenv("SIGMA_DIR", "Sigma Exploiot rules/Sigma_Exploiot_rules")
LCEL_DIR      = os.getenv("LCEL_DIR", "LCEL_data")
CVE_DIR       = os.getenv("CVE_DIR", "cve_cwe_data/CVE")
CWE_DIR       = os.getenv("CWE_DIR", "cve_cwe_data/CWE")
CAPEC_DIR     = os.getenv("CAPEC_DIR", "stix_data/capec_latest/attack_documents")
ICS_DIR       = os.getenv("ICS_DIR", "stix_data/cti-master/ics-attack/processed-attack-pattern")
ASSET_DIR     = os.getenv("ASSET_DIR", "assets_test/sample_assets.jsonl")
QUERY_DIR     = os.getenv("QUERY_DIR", "query_examples")

# === FAISS index dirs ===
SCENARIO1_INDEX = os.getenv("SCENARIO1_INDEX", "scenario1_faiss_index")
SIGMA_INDEX     = os.getenv("SIGMA_INDEX", "SIGMA_faiss_index")
CVE_INDEX       = os.getenv("CVE_INDEX", "CVE_faiss_index")
CWE_INDEX       = os.getenv("CWE_INDEX", "CWE_faiss_index")
CAPEC_INDEX     = os.getenv("CAPEC_INDEX", "CAPEC_faiss_index")
ICS_INDEX       = os.getenv("ICS_INDEX", "ICS_faiss_index")
LCEL_INDEX      = os.getenv("LCEL_INDEX", "LCEL_Examples_Index")
ASSET_INDEX     = os.getenv("ASSET_INDEX", "asset_Examples_Index")
QUERY_INDEX     = os.getenv("QUERY_INDEX", "query_examples_index")

# === optional employee/network files (used by DocumentAnalysisAgent) ===
EMPLOYEE_XLSX   = os.getenv("EMPLOYEE_XLSX", "employee_data/CompanyX_EmployeeData.xlsx")
NETWORK_CSV     = os.getenv("NETWORK_CSV", "employee_data/ProxMoxServer1_Map.csv")

# === drafts & logs ===
DRAFTS_DIR        = os.getenv("DRAFTS_DIR", "drafts")
DRAFT_CHECKPOINT  = os.getenv("DRAFT_CHECKPOINT", os.path.join(DRAFTS_DIR, "asset_drafts.checkpoint.jsonl"))
DRAFT_RUNS_DIR    = os.getenv("DRAFT_RUNS_DIR", os.path.join(DRAFTS_DIR, "runs"))
RETRIEVAL_LOG     = os.getenv("RETRIEVAL_LOG", os.path.join(DRAFTS_DIR, "retrieval.log.jsonl"))

# === consolidated maps (handy for loops) ===
DATASETS = {
    "scenario1": {"src": SCENARIO1_DIR, "index": SCENARIO1_INDEX, "source_name": "scenario1_data"},
    "sigma":     {"src": SIGMA_DIR,     "index": SIGMA_INDEX,     "source_name": "sigma_rule"},
    "cve":       {"src": CVE_DIR,       "index": CVE_INDEX,       "source_name": "CVE_data"},
    "cwe":       {"src": CWE_DIR,       "index": CWE_INDEX,       "source_name": "CWE_data"},
    "capec":     {"src": CAPEC_DIR,     "index": CAPEC_INDEX,     "source_name": "CAPEC_data"},
    "ics":       {"src": ICS_DIR,       "index": ICS_INDEX,       "source_name": "ICS_data"},
    "lcel":      {"src": LCEL_DIR,      "index": LCEL_INDEX,      "source_name": "LCEL_Examples"},
    "asset":     {"src": ASSET_DIR,     "index": ASSET_INDEX,     "source_name": "asset_Examples"},
    "query":     {"src": QUERY_DIR,     "index": QUERY_INDEX,     "source_name": "query_examples"},
}

__all__ = [
    "STORAGE_PATH",
    "SCENARIO1_DIR", "SIGMA_DIR", "LCEL_DIR", "CVE_DIR", "CWE_DIR", "CAPEC_DIR", "ICS_DIR", "ASSET_DIR",
    "SCENARIO1_INDEX", "SIGMA_INDEX", "CVE_INDEX", "CWE_INDEX", "CAPEC_INDEX", "ICS_INDEX", "LCEL_INDEX", "ASSET_INDEX",
    "EMPLOYEE_XLSX", "NETWORK_CSV", "QUERY_DIR", "QUERY_INDEX",
    "DRAFTS_DIR", "DRAFT_CHECKPOINT", "DRAFT_RUNS_DIR", "RETRIEVAL_LOG",
    "DATASETS",
]
