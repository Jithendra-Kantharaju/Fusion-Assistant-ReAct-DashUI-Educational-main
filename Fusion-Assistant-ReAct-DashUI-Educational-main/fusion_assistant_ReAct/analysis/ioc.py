import re
from typing import List, Dict
def extract_iocs(text: str) -> Dict[str, list]:
    urls = re.findall(r'https?://[^\s]+', text or "")
    ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text or "")
    ports = re.findall(r'(?<=:)(\d{1,5})\b', text or "")
    return {"urls": list(set(urls)), "ips": list(set(ips)), "ports": list(set(ports))}
